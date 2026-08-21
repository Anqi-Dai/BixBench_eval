"""Build the capsule survey table: what each capsule is, and what it costs to run.

Two different things were being tracked in one place. `results/spend_log.csv` is a
run ledger -- one row per invocation, including grading runs and preflights -- and
is the accounting record. What survey and piloting actually need is one row per
*capsule*, joining what the capsule is about to what it cost when run.

This produces that second table by joining three sources:

  * `BixBench.jsonl`      -- questions, topics, hypothesis, source paper, verifier mix
  * `results/spend_log.csv`  -- measured cost and wall clock per replica
  * `results/agent_runs.csv` -- actions used, ceiling hits, missing answers

Capsules that have not been piloted still appear, with the metadata filled in and
the measured columns blank, so the table doubles as a candidate list.

Usage:
    python py/pilot_table.py --out results/capsule_pilot_log.csv
"""

import argparse
import ast
import collections
import csv
import json
import re
import statistics
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO = Path(__file__).resolve().parent.parent
REPO_ID = "futurehouse/BixBench"

FIELDS = [
    "capsule", "n_questions", "n_llm_verifier", "n_str_verifier", "n_range_verifier",
    "mean_question_chars", "topics", "hypothesis", "source_paper", "family_size",
    "piloted", "usd_per_replica", "min_per_replica", "usd_per_rollout",
    "min_per_rollout", "actions_min", "actions_median", "actions_max",
    "n_hit_ceiling", "n_empty_answer", "n_correct_exact",
]


def parse_categories(raw):
    """categories is stored as a comma string in most rows and a list repr in some."""
    raw = (raw or "").strip()
    if raw.startswith("["):
        try:
            return [str(x).strip() for x in ast.literal_eval(raw) if str(x).strip()]
        except (ValueError, SyntaxError):
            pass
    return [p.strip() for p in raw.split(",") if p.strip()]


def load_metadata():
    path = hf_hub_download(REPO_ID, "BixBench.jsonl", repo_type="dataset")
    return [json.loads(line) for line in open(path)]


def load_measured():
    """Cost and wall clock per capsule, from the run ledger.

    Only agent runs are relevant here, and only the most recent entry per capsule:
    bix-8 and bix-1 were each run twice, the first time under conditions later
    found to be invalid, and the reruns supersede them.
    """
    ledger = REPO / "results/spend_log.csv"
    out = {}
    if not ledger.exists():
        return out
    for r in csv.DictReader(ledger.open()):
        if not r["run"].startswith("agent_"):
            continue
        cap = r["run"].split("_")[1]
        wall = (r.get("wall_clock_min") or "").lstrip("~")
        out[cap] = {  # later rows overwrite earlier, keeping the rerun
            "usd": float(r["usd"]),
            "min": float(wall) if wall else None,
        }
    return out


def load_trajectories():
    """Per-capsule action counts and failure flags from the tidy run output."""
    path = REPO / "results/agent_runs.csv"
    out = collections.defaultdict(
        lambda: {"acts": [], "ceiling": 0, "empty": 0, "exact": 0}
    )
    if not path.exists():
        return out
    for r in csv.DictReader(path.open()):
        c = out[r["capsule"]]
        if r["num_actions"]:
            c["acts"].append(int(r["num_actions"]))
        c["ceiling"] += r["hit_ceiling"] == "True"
        c["empty"] += r["has_answer"] == "False"
        # A crude exactness check only: real grading is a separate replicated step,
        # since the grader is itself a noise source.
        ideal = (r["ideal_answer"] or "").strip().lower()
        got = re.sub(r"</?answer>", "", r["agent_answer"] or "").strip().lower()
        if ideal and got and (got == ideal or ideal in got):
            c["exact"] += 1
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/capsule_pilot_log.csv")
    ap.add_argument("--piloted-only", action="store_true")
    args = ap.parse_args()

    rows = load_metadata()
    measured = load_measured()
    traj = load_trajectories()

    # Family size: how many *capsules* share this source paper. Counting rows would
    # count questions instead, inflating every family several-fold. Unlabeled
    # papers are not a family -- sixteen capsules carry the placeholder
    # "Not Available" and have nothing in common.
    fam_caps = collections.defaultdict(set)
    for r in rows:
        if r["paper"] and r["paper"] != "Not Available":
            fam_caps[r["paper"]].add(r["short_id"])
    fam = {k: len(v) for k, v in fam_caps.items()}

    caps = collections.defaultdict(
        lambda: {"qs": [], "cats": set(), "modes": collections.Counter(),
                 "hyp": "", "paper": ""}
    )
    for r in rows:
        c = caps[r["short_id"]]
        c["qs"].append(r["question"])
        c["cats"].update(parse_categories(r["categories"]))
        c["modes"][r["eval_mode"]] += 1
        c["hyp"] = r.get("hypothesis") or ""
        c["paper"] = r.get("paper") or ""

    out_rows = []
    for sid in sorted(caps, key=lambda s: int(s.split("-")[1])):
        c = caps[sid]
        m = measured.get(sid)
        t = traj.get(sid)
        acts = sorted(t["acts"]) if t and t["acts"] else []
        n = len(c["qs"])
        paper = c["paper"] if c["paper"] != "Not Available" else ""
        out_rows.append({
            "capsule": sid,
            "n_questions": n,
            "n_llm_verifier": c["modes"]["llm_verifier"],
            "n_str_verifier": c["modes"]["str_verifier"],
            "n_range_verifier": c["modes"]["range_verifier"],
            "mean_question_chars": sum(map(len, c["qs"])) // n,
            "topics": "; ".join(sorted(c["cats"])),
            "hypothesis": c["hyp"].replace("\n", " ").strip(),
            "source_paper": paper,
            "family_size": fam.get(c["paper"], 1) if paper else 1,
            "piloted": bool(m),
            "usd_per_replica": f"{m['usd']:.4f}" if m else "",
            "min_per_replica": f"{m['min']:.1f}" if m and m["min"] else "",
            "usd_per_rollout": f"{m['usd']/n:.4f}" if m else "",
            "min_per_rollout": f"{m['min']/n:.2f}" if m and m["min"] else "",
            "actions_min": min(acts) if acts else "",
            "actions_median": int(statistics.median(acts)) if acts else "",
            "actions_max": max(acts) if acts else "",
            "n_hit_ceiling": t["ceiling"] if t else "",
            "n_empty_answer": t["empty"] if t else "",
            "n_correct_exact": t["exact"] if t else "",
        })

    if args.piloted_only:
        out_rows = [r for r in out_rows if r["piloted"]]

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out_rows)
    print(f"wrote {out} ({len(out_rows)} capsules, "
          f"{sum(r['piloted'] for r in out_rows)} piloted)")

    piloted = [r for r in out_rows if r["piloted"]]
    if piloted:
        print(f"\n{'capsule':8s} {'n':>2s} {'$/rep':>7s} {'min/rep':>7s} {'$/roll':>7s} "
              f"{'actions':>12s} {'ceil':>4s} {'empty':>5s} {'exact':>5s}  topics")
        for r in sorted(piloted, key=lambda r: float(r["usd_per_rollout"])):
            a = f"{r['actions_min']}-{r['actions_median']}-{r['actions_max']}"
            print(f"{r['capsule']:8s} {r['n_questions']:2d} {r['usd_per_replica']:>7s} "
                  f"{r['min_per_replica']:>7s} {r['usd_per_rollout']:>7s} {a:>12s} "
                  f"{str(r['n_hit_ceiling']):>4s} {str(r['n_empty_answer']):>5s} "
                  f"{str(r['n_correct_exact']):>5s}  {r['topics'][:44]}")


if __name__ == "__main__":
    main()
