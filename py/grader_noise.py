"""Measure grader noise and grader self-preference on BixBench open answers.

Fills a 2x2 of answer-set x grader model, with K independent grading replicates
in every cell, and persists one row per grade.

Why this design:

  * **Grader noise.** The harness grades open answers with an LLM at temperature
    1.0, so the same answer can receive different grades on different calls.
    Re-grading identical answers K times isolates that noise exactly, because the
    only thing varying is the grader's own sampling.

  * **Self-preference.** A raw gap between two graders confounds favoritism with
    leniency: a grader that passes everything looks self-preferring on its own
    model's answers. Crossing two answer sets with two graders separates them,
    because self-preference is the interaction

        (A - B) - (C - D)

    where A/B are one answer set graded by each grader and C/D the other. A
    uniformly lenient grader raises A and C together and cancels; a genuinely
    better answer set raises A and B together and cancels.

No agent runs are needed. Both answer sets already exist as zero-shot baselines
in the upstream repo, so this costs grading calls only.

Grading goes through the harness's own `GradeAnswer`, not a reimplementation, so
what gets measured is the real grader including its quirks -- notably that
`str_verifier` falls through to the LLM whenever exact and substring matching
both fail, and that `range_verifier` is LLM-based in the open-answer path.

Output is tidy: one row per (answer_set, grader, question, replicate), ready for
the multilevel model in R.

Usage:
    # cheap auth + model-availability check, 1 call per grader
    python py/grader_noise.py --preflight

    # the real run
    python py/grader_noise.py --replicates 10 --out results/grader_noise.csv
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

# The harness lives in a sibling clone; its .env is where the API keys are,
# because generate_zeroshot_evals.py resolves Path(".env") against the working
# directory it is run from.
UPSTREAM = Path(__file__).resolve().parent.parent.parent / "BixBench-upstream"
REPO = Path(__file__).resolve().parent.parent

# The harness is a plain package directory rather than an installed distribution,
# so it only imports when the clone is on the path. Adding it explicitly lets this
# script run from anywhere instead of only from the upstream working directory.
sys.path.insert(0, str(UPSTREAM))

from bixbench.graders import OpenEndedGrader  # noqa: E402
from lmi import LiteLLMModel  # noqa: E402

# The two shipped zero-shot answer sets. The filenames say "grader" but the model
# named is the *answering* model -- every shipped baseline was graded by gpt-4o.
ANSWER_SETS = {
    "gpt-4o": "bixbench-v1.5_results/zero_shot_baselines/gpt-4o-grader-openended.csv",
    "claude-3-5-sonnet": (
        "bixbench-v1.5_results/zero_shot_baselines/"
        "claude-3-5-sonnet-latest-grader-openended.csv"
    ),
}

# The agent's own answers, from results/agent_runs.csv rather than the shipped
# baselines. This is the substrate that matters: the zero-shot baselines score
# 2.9% correct, so almost every answer is unambiguously wrong and graders agree
# trivially. Agent answers are borderline in the way that actually produces
# disagreement -- 3.87 against a ground truth of 3.83, or 8.1e-194 against
# "p < 2.2e-16".
AGENT_RUNS = "results/agent_runs.csv"

# Both graders are pinned to dated snapshots rather than floating aliases
# ("gpt-4o", "claude-sonnet-5"). In a study whose subject is grader noise, an
# alias silently repointing to a new model mid-run would be indistinguishable
# from the noise being measured, so drift has to be ruled out by construction.
#
# claude-3-5-sonnet, the judge the paper names and the model that produced the
# Claude answer set, has been retired and is no longer callable. The Claude
# grader is therefore a later generation than the answers it grades, which makes
# the self-grading cell a *family* comparison rather than strict self-preference.
DEFAULT_GRADERS = ["gpt-4o-2024-11-20", "anthropic/claude-sonnet-4-5-20250929"]

# Columns written per grade. Wide enough that the R side needs no lookups back
# into the source CSVs.
FIELDS = [
    "answer_set", "grader", "grader_temperature", "replicate",
    "uuid", "capsule", "eval_mode", "llm_called",
    "grade", "correct", "refusal", "raw_verdict",
]


def capsule_of(uuid: str) -> str:
    """Capsule id from a question uuid, tolerating upstream's mixed case."""
    m = re.match(r"[Bb]ix-(\d+)-q\d+$", uuid)
    return f"bix-{m.group(1)}" if m else "unknown"


def hits_llm(row) -> bool:
    """Whether this question will actually reach the LLM grader.

    Mirrors `_grade_str_verifier` in bixbench/graders.py. `llm_verifier` and
    `range_verifier` always call the LLM in the open-answer path; `str_verifier`
    short-circuits only when the normalized answer matches the target exactly or
    is a substring of it. Recording this per row keeps deterministic grades from
    being mistaken for a grader that happened to be stable.
    """
    if row["evaluation_mode"] != "str_verifier":
        return True
    clean = lambda s: re.sub(r"[^a-zA-Z0-9]", "", str(s)).lower()  # noqa: E731
    t, p = clean(row["target"]), clean(row["predicted"])
    return not (p == t or p in t)


def load_answer_sets(selected):
    """Read the shipped baselines, tagging each row with its answering model."""
    out = []
    for name in selected:
        path = UPSTREAM / ANSWER_SETS[name]
        if not path.exists():
            sys.exit(f"missing answer set: {path}")
        for row in csv.DictReader(path.open()):
            row["answer_set"] = name
            out.append(row)
    return out


def load_agent_answers(capsules, questions_by_id):
    """Read the agent's answers and reshape them into the grader's row format.

    Trajectories with no answer are skipped rather than graded. Sending an empty
    submission to the grader would return "incorrect", which is exactly the
    collapse this project documents -- an agent that never answered is not an
    agent that answered wrongly.

    The question text lives in the dataset metadata rather than in agent_runs.csv,
    so it is joined back in by question_id; the grader prompt needs it.
    """
    path = REPO / "results/agent_runs.csv"
    out = []
    for r in csv.DictReader(path.open()):
        if capsules and r["capsule"] not in capsules:
            continue
        if r["has_answer"] != "True":
            continue
        q = questions_by_id.get(r["question_id"])
        if q is None:
            continue
        out.append({
            "uuid": f"{r['question_id']}_replica_{r['replica']}",
            "question": q,
            "predicted": r["agent_answer"],
            "target": r["ideal_answer"],
            "evaluation_mode": r["eval_mode"] or "llm_verifier",
            "answer_set": "claude-agent",
        })
    return out


def load_question_text():
    """question_id -> question text, from the dataset metadata."""
    from huggingface_hub import hf_hub_download
    path = hf_hub_download("futurehouse/BixBench", "BixBench.jsonl",
                           repo_type="dataset")
    return {json.loads(line)["question_id"]: json.loads(line)["question"]
            for line in open(path)}


def make_client(model_name: str, temperature: float):
    """One LLM client per grader model, reused across all its calls."""
    return LiteLLMModel(
        name=model_name,
        config={"name": model_name, "temperature": temperature, "num_retries": 5},
    )


async def grade_one(client, row, sem):
    """Grade a single answer, holding a concurrency slot for the call.

    This calls `OpenEndedGrader` directly rather than `GradeAnswer`. The two are
    equivalent for open answers -- `GradeAnswer` merely constructs an
    `OpenEndedGrader` and forwards to it -- but the inner class returns the full
    `GradeResult`, which carries the grader's raw text. That matters because the
    harness collapses every non-"correct" verdict, refusals included, into
    "incorrect"; keeping the raw text is the only way to tell an honest refusal
    apart from a confident wrong answer after the fact. It also avoids
    `GradeAnswer`'s unconditional debug printing.

    partial_match and llm_match mirror how grade_outputs.py invokes grading for
    open answers; changing them would measure a grader the harness never uses.
    """
    async with sem:
        grader = OpenEndedGrader(
            evaluation_mode=row.get("evaluation_mode", "llm_verifier"),
            llm_client=client,
        )
        return await grader.grade(
            question=row["question"],
            target=str(row["target"]),
            predicted=str(row["predicted"]),
            partial_match=True,
            llm_match=True,
        )


def load_done(path: Path) -> set:
    """Keys already graded, so an interrupted paid run can resume cheaply."""
    if not path.exists():
        return set()
    with path.open() as fh:
        return {
            (r["answer_set"], r["grader"], r["uuid"], r["replicate"])
            for r in csv.DictReader(fh)
        }


async def main_async(args):
    load_dotenv(UPSTREAM / ".env")
    for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        if not os.getenv(var):
            sys.exit(f"{var} not set; expected it in {UPSTREAM / '.env'}")

    if args.agent_answers:
        rows = load_agent_answers(set(args.capsules), load_question_text())
        print(f"grading {len(rows)} agent answers "
              f"({', '.join(sorted(args.capsules))})")
    else:
        rows = load_answer_sets(args.answer_sets)
    # A capped run exists to prove the plumbing works, not to measure anything;
    # the cap takes the first N questions of each answer set so both sides stay
    # aligned on the same questions.
    if args.max_questions:
        capped = []
        for name in args.answer_sets:
            capped += [r for r in rows if r["answer_set"] == name][: args.max_questions]
        rows = capped
    clients = {m: make_client(m, args.temperature) for m in args.graders}

    # A preflight grades one row per grader. It costs a couple of calls and
    # catches a bad key or an unavailable model id before a paid run starts.
    if args.preflight:
        for name, client in clients.items():
            try:
                res = await grade_one(client, rows[0], asyncio.Semaphore(1))
                print(f"  ok   {name}: grade={res.grade} correct={res.correct}")
            except Exception as e:
                print(f"  FAIL {name}: {type(e).__name__}: {str(e)[:200]}")
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = load_done(out) if args.resume else set()
    if done:
        print(f"resuming: {len(done)} grades already recorded")

    # Every cell of the design: answer set x grader x question x replicate.
    work = [
        (row, gname, k)
        for k in range(args.replicates)
        for gname in clients
        for row in rows
        if (row["answer_set"], gname, row["uuid"], str(k)) not in done
    ]
    llm_calls = sum(1 for row, _, _ in work if hits_llm(row))
    print(f"{len(work)} grades to run ({llm_calls} of them real LLM calls)")
    if not work:
        return

    sem = asyncio.Semaphore(args.concurrency)
    write_header = not out.exists() or not args.resume
    mode = "a" if (args.resume and out.exists()) else "w"

    # Results are appended as they land rather than held in memory and written at
    # the end, so a crash or rate-limit wall never discards work already paid for.
    with out.open(mode, newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        if write_header:
            w.writeheader()
        completed = 0
        for chunk_start in range(0, len(work), args.flush_every):
            chunk = work[chunk_start : chunk_start + args.flush_every]
            results = await asyncio.gather(
                *(grade_one(clients[g], row, sem) for row, g, _ in chunk),
                return_exceptions=True,
            )
            for (row, gname, k), res in zip(chunk, results, strict=True):
                if isinstance(res, Exception):
                    print(f"  error {row['uuid']} {gname} rep{k}: "
                          f"{type(res).__name__}: {str(res)[:120]}")
                    continue
                # The harness maps any verdict other than "correct" to
                # incorrect, so the raw tag is kept alongside the numeric grade.
                raw = re.search(r"<grade>\s*(.*?)\s*</grade>",
                                getattr(res, "raw_response", "") or "", re.DOTALL)
                w.writerow({
                    "answer_set": row["answer_set"], "grader": gname,
                    "grader_temperature": args.temperature, "replicate": k,
                    "uuid": row["uuid"], "capsule": capsule_of(row["uuid"]),
                    "eval_mode": row["evaluation_mode"], "llm_called": hits_llm(row),
                    "grade": res.grade, "correct": res.correct,
                    "refusal": res.refusal,
                    "raw_verdict": raw.group(1).strip().lower() if raw else "",
                })
            fh.flush()
            completed += len(chunk)
            print(f"  {completed}/{len(work)}")
    print(f"wrote {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--replicates", type=int, default=10)
    ap.add_argument("--temperature", type=float, default=1.0,
                    help="grader temperature; 1.0 is the harness default and the "
                         "setting whose noise this study is about")
    ap.add_argument("--graders", nargs="+", default=DEFAULT_GRADERS)
    ap.add_argument("--answer-sets", nargs="+", default=list(ANSWER_SETS),
                    choices=list(ANSWER_SETS))
    ap.add_argument("--max-questions", type=int, default=0,
                    help="cap questions per answer set; 0 means all. For smoke "
                         "tests only -- a capped run is not a valid measurement")
    ap.add_argument("--agent-answers", action="store_true",
                    help="grade the agent's own answers from results/agent_runs.csv "
                         "instead of the shipped zero-shot baselines")
    ap.add_argument("--capsules", nargs="+",
                    default=["bix-8", "bix-49", "bix-26"],
                    help="capsules to include when --agent-answers is set")
    ap.add_argument("--out", default="results/grader_noise.csv")
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--flush-every", type=int, default=200,
                    help="results written to disk after each batch of this size")
    ap.add_argument("--resume", action="store_true",
                    help="skip grades already present in --out")
    ap.add_argument("--preflight", action="store_true",
                    help="grade one row per grader to check keys and model ids")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
