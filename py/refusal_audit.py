"""Measure how much of BixBench's "incorrect" is actually the model refusing.

The harness asks its grader to return one of three verdicts -- `correct`,
`incorrect`, or `refused` -- and then discards the third. `_parse_grade_response`
in bixbench/graders.py maps everything that is not `correct` to `INCORRECT`,
even though `GradeType.REFUSED` exists. So in the reported open-answer scores, a
model that hallucinates a confident wrong number and a model that correctly says
it lacks the data are indistinguishable.

This script recovers the discarded distinction. It sends the harness's own
grading prompts verbatim and records the raw verdict, rather than reimplementing
any grading logic: the same prompt and the same parse rule produce the same
`correct`/`not correct` split the harness would produce, with the third category
preserved.

Only questions that actually reach the LLM are graded, mirroring the harness --
`str_verifier` rows short-circuit when the answer matches the target exactly or
as a substring, and those never see a grader at all.

Token usage is read back from each call, so cost is recorded from actuals rather
than inferred from prompt sizes.

Usage:
    python py/refusal_audit.py --out results/refusal_audit.csv
"""

import argparse
import asyncio
import csv
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

UPSTREAM = Path(__file__).resolve().parent.parent.parent / "BixBench-upstream"
sys.path.insert(0, str(UPSTREAM))

from aviary.core import Message  # noqa: E402
from bixbench.prompts import (  # noqa: E402
    OPEN_ENDED_GRADING_PROMPT,
    OPEN_ENDED_RANGE_GRADING_PROMPT,
)
from lmi import LiteLLMModel  # noqa: E402

ANSWER_SETS = {
    "gpt-4o": "bixbench-v1.5_results/zero_shot_baselines/gpt-4o-grader-openended.csv",
    "claude-3-5-sonnet": (
        "bixbench-v1.5_results/zero_shot_baselines/"
        "claude-3-5-sonnet-latest-grader-openended.csv"
    ),
}

# gpt-4o is the grader the shipped code actually uses, so the audit speaks to the
# numbers a reproduction from this repo would produce. Pinned, not the floating
# "gpt-4o" alias, so the measurement stays reproducible.
DEFAULT_GRADER = "gpt-4o-2024-11-20"

# USD per million tokens, list pricing.
PRICES = {
    "gpt-4o-2024-11-20": (2.50, 10.00),
    "anthropic/claude-sonnet-4-5-20250929": (3.00, 15.00),
}

FIELDS = [
    "answer_set", "grader", "uuid", "capsule", "eval_mode",
    "raw_verdict", "harness_grade", "harness_correct",
    "prompt_tokens", "completion_tokens",
]


def clean(s):
    return re.sub(r"[^a-zA-Z0-9]", "", str(s)).lower()


def hits_llm(row):
    """Whether the harness would actually call the grader for this row."""
    if row["evaluation_mode"] != "str_verifier":
        return True
    t, p = clean(row["target"]), clean(row["predicted"])
    return not (p == t or p in t)


def capsule_of(uuid):
    m = re.match(r"[Bb]ix-(\d+)-q\d+$", uuid)
    return f"bix-{m.group(1)}" if m else "unknown"


def build_prompt(row):
    """The harness picks its template by evaluation_mode; this mirrors that."""
    tpl = (
        OPEN_ENDED_RANGE_GRADING_PROMPT
        if row["evaluation_mode"] == "range_verifier"
        else OPEN_ENDED_GRADING_PROMPT
    )
    return tpl.format(
        question=row["question"], target=row["target"], predicted=row["predicted"]
    )


async def grade(client, row, sem):
    """One grading call, returning the raw verdict plus real token counts."""
    async with sem:
        res = await client.call_single([Message(content=build_prompt(row))])
    text = res.text or ""
    m = re.search(r"<grade>\s*(.*?)\s*</grade>", text, re.DOTALL)
    verdict = m.group(1).strip().lower() if m else "UNPARSEABLE"
    return verdict, res.prompt_count or 0, res.completion_count or 0


async def main_async(args):
    load_dotenv(UPSTREAM / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY not set")

    # Only rows the harness would send to an LLM; the rest are decided by string
    # matching and can never be a refusal.
    rows = []
    for name, rel in ANSWER_SETS.items():
        for r in csv.DictReader((UPSTREAM / rel).open()):
            if hits_llm(r):
                r["answer_set"] = name
                rows.append(r)
    print(f"{len(rows)} LLM-graded answers across {len(ANSWER_SETS)} answer sets")

    client = LiteLLMModel(
        name=args.grader,
        config={"name": args.grader, "temperature": args.temperature, "num_retries": 5},
    )
    sem = asyncio.Semaphore(args.concurrency)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Rate limits drop individual calls rather than failing the run, so already
    # graded rows are skipped and the rest appended. Without this, a partial run
    # would have to be repaid in full.
    done = set()
    if args.resume and out.exists():
        with out.open() as fh:
            done = {(r["answer_set"], r["uuid"]) for r in csv.DictReader(fh)}
        rows = [r for r in rows if (r["answer_set"], r["uuid"]) not in done]
        print(f"resuming: {len(done)} already graded, {len(rows)} remaining")
        if not rows:
            return

    tot_in = tot_out = 0
    mode = "a" if (args.resume and out.exists()) else "w"
    with out.open(mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if mode == "w":
            w.writeheader()
        for start in range(0, len(rows), 100):
            chunk = rows[start : start + 100]
            results = await asyncio.gather(
                *(grade(client, r, sem) for r in chunk), return_exceptions=True
            )
            for r, res in zip(chunk, results, strict=True):
                if isinstance(res, Exception):
                    print(f"  error {r['uuid']}: {type(res).__name__}")
                    continue
                verdict, pin, pout = res
                tot_in += pin
                tot_out += pout
                # Reproduce the harness's lossy mapping alongside the raw verdict
                # so the two can be compared directly.
                w.writerow({
                    "answer_set": r["answer_set"], "grader": args.grader,
                    "uuid": r["uuid"], "capsule": capsule_of(r["uuid"]),
                    "eval_mode": r["evaluation_mode"], "raw_verdict": verdict,
                    "harness_grade": 1 if verdict == "correct" else 0,
                    "harness_correct": verdict == "correct",
                    "prompt_tokens": pin, "completion_tokens": pout,
                })
            fh.flush()
            print(f"  {min(start+100, len(rows))}/{len(rows)}")

    pin_price, pout_price = PRICES.get(args.grader, (0, 0))
    cost = tot_in / 1e6 * pin_price + tot_out / 1e6 * pout_price
    print(f"\nwrote {out}")
    print(f"tokens: {tot_in:,} in / {tot_out:,} out   actual cost: ${cost:.4f}")

    # Append to the running spend ledger so project cost is a record, not a memory.
    ledger = Path("results/spend_log.csv")
    new = not ledger.exists()
    with ledger.open("a", newline="") as fh:
        lw = csv.writer(fh)
        if new:
            lw.writerow(["run", "model", "calls", "prompt_tokens",
                         "completion_tokens", "usd", "basis"])
        lw.writerow([args.label, args.grader, len(rows), tot_in, tot_out,
                     f"{cost:.4f}", "actual"])
    print(f"logged to {ledger}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grader", default=DEFAULT_GRADER)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--out", default="results/refusal_audit.csv")
    ap.add_argument("--label", default="refusal_audit",
                    help="name recorded in the spend ledger")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--resume", action="store_true",
                    help="skip rows already present in --out")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
