"""Turn agent trajectory JSONs into a tidy CSV, and extract notebooks for review.

Each run writes one JSON per question per replica, carrying the submitted answer,
the ground truth, notebook statistics, and the full notebook inline. This flattens
those into one row per (capsule, question, replica) -- the handoff to the R
analysis -- and optionally writes each notebook out as a real .ipynb so the
failure-taxonomy phase can read what the agent actually did.

Answers are deliberately *not* graded here. Grading is a separate, replicated
step, because the grader is itself a noise source and has to be measured rather
than folded silently into the run record.

Usage:
    python py/collect_trajectories.py --run pricing_bix8_claude45 \
        --out results/agent_runs.csv --write-notebooks
"""

import argparse
import csv
import json
import re
from pathlib import Path

UPSTREAM = Path(__file__).resolve().parent.parent.parent / "BixBench-upstream"
REPO = Path(__file__).resolve().parent.parent

FIELDS = [
    "run_name", "model", "capsule", "question_id", "replica",
    "agent_answer", "ideal_answer", "eval_mode",
    "num_actions", "n_steps", "done", "truncated", "hit_ceiling",
    "code_cells", "code_lines", "images", "tables",
    "answer_chars", "has_answer", "notebook_path",
]


def parse_name(path):
    """Recover question id and replica index from the trajectory filename."""
    m = re.match(r"(.+?)_replica_(\d+)\.json$", path.name)
    if m:
        return m.group(1), int(m.group(2))
    return path.stem, 0


def capsule_of(qid):
    m = re.match(r"[Bb]ix-(\d+)-q\d+$", qid)
    return f"bix-{m.group(1)}" if m else "unknown"


def strip_answer_tags(s):
    """The agent wraps its submission in <answer> tags; keep both forms.

    The raw string is what the grader actually receives, so it is preserved
    verbatim in `agent_answer`. This helper exists only for readability when
    eyeballing results, and is not used to alter what gets graded.
    """
    m = re.search(r"<answer>\s*(.*?)\s*</answer>", s or "", re.DOTALL)
    return m.group(1).strip() if m else (s or "").strip()



def terminal_flags(json_path):
    """Read the trajectory's terminal state from its companion .jsonl.

    A run that exhausts max_steps is truncated rather than finished, and its
    answer is whatever the agent happened to have at the ceiling. Left
    unrecorded, truncated runs read as ordinary disagreement between replicates
    and would inflate any measure of inconsistency -- so the flags are carried
    into the tidy output and excluded or modeled downstream rather than silently
    pooled.
    """
    jl = json_path.with_suffix(".jsonl")
    if not jl.exists():
        return None, None, None
    recs = [json.loads(line) for line in jl.open() if line.strip()]
    if len(recs) == 1 and isinstance(recs[0], dict) and "steps" in recs[0]:
        recs = recs[0]["steps"]
    if not recs:
        return 0, None, None
    last = recs[-1]
    return len(recs), last.get("done"), last.get("truncated")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run_name subdirectory to collect")
    ap.add_argument("--trajectories-root", default="data/trajectories")
    ap.add_argument("--out", default="results/agent_runs.csv")
    ap.add_argument("--write-notebooks", action="store_true",
                    help="extract each inline notebook to notebooks/raw/<run>/")
    ap.add_argument("--max-steps", type=int, default=20,
                    help="the run's step ceiling, used to flag trajectories that "
                         "finished at or near it")
    args = ap.parse_args()

    # Trajectories land under <root>/<config dir>/<run_name>/, so the run name is
    # searched for rather than assumed to sit at a fixed depth.
    root = UPSTREAM / args.trajectories_root
    dirs = [d for d in root.rglob(args.run) if d.is_dir()]
    if not dirs:
        raise SystemExit(f"no directory named {args.run!r} under {root}")
    files = sorted(f for d in dirs for f in d.glob("*_replica_*.json"))
    if not files:
        files = sorted(f for d in dirs for f in d.glob("*.json"))
    print(f"found {len(files)} trajectories in {dirs[0]}")

    nb_dir = REPO / "notebooks/raw" / args.run
    if args.write_notebooks:
        nb_dir.mkdir(parents=True, exist_ok=True)

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for f in files:
        d = json.loads(f.read_text())
        qid, rep = parse_name(f)
        stats = d.get("notebook_stats") or {}

        # Write the notebook out only when asked: these are large, and only a
        # curated few belong in version control.
        nb_path = ""
        if args.write_notebooks and d.get("nb"):
            p = nb_dir / f"{qid}_replica_{rep}.ipynb"
            p.write_text(json.dumps(d["nb"], indent=1))
            nb_path = str(p.relative_to(REPO))

        answer = d.get("agent_answer") or ""
        n_steps, done, trunc = terminal_flags(f)
        actions = d.get("num_actions")
        # Flag anything that ran to the ceiling even if the harness called it
        # done: an agent that submits on its very last permitted step was
        # constrained by the budget, not by having finished.
        hit = (isinstance(actions, int) and actions >= args.max_steps - 1) or bool(trunc)
        rows.append({
            "run_name": d.get("run_name", args.run),
            "model": d.get("model", ""),
            "capsule": capsule_of(qid),
            "question_id": qid,
            "replica": rep,
            "agent_answer": answer,
            "ideal_answer": d.get("ideal_answer", ""),
            "eval_mode": (d.get("metadata") or {}).get("eval_mode", ""),
            "num_actions": actions if actions is not None else "",
            "n_steps": n_steps if n_steps is not None else "",
            "done": done, "truncated": trunc, "hit_ceiling": hit,
            "code_cells": stats.get("code_cells", ""),
            "code_lines": stats.get("code_lines", ""),
            "images": stats.get("images", ""),
            "tables": stats.get("tables", ""),
            "answer_chars": len(answer),
            "has_answer": bool(answer.strip()),
            "notebook_path": nb_path,
        })

    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {out} ({len(rows)} rows)")

    # Truncation is a validity problem, not a curiosity: it has to be visible
    # before any self-consistency number is computed from these rows.
    ceil_hits = [r for r in rows if r["hit_ceiling"]]
    no_answer = [r for r in rows if not r["has_answer"]]
    print(f"  step ceiling ({args.max_steps}): {len(ceil_hits)} trajectory(ies) at or near it"
          + (f" -> {', '.join(r['question_id'] for r in ceil_hits)}" if ceil_hits else ""))
    print(f"  empty answers: {len(no_answer)}"
          + (f" -> {', '.join(r['question_id'] for r in no_answer)}" if no_answer else ""))
    used = [r["num_actions"] for r in rows if isinstance(r["num_actions"], int)]
    if used:
        print(f"  actions used: min {min(used)}, max {max(used)}, ceiling {args.max_steps}"
              f"  (headroom {args.max_steps - max(used)})")

    # A quick orientation summary; real analysis happens in R.
    for r in sorted(rows, key=lambda r: r["question_id"]):
        got = strip_answer_tags(r["agent_answer"])[:60]
        print(f"  {r['question_id']:12s} rep{r['replica']} "
              f"actions={r['num_actions']:>3} cells={r['code_cells']:>3}  "
              f"ideal={str(r['ideal_answer'])[:22]:22s} got={got}")


if __name__ == "__main__":
    main()
