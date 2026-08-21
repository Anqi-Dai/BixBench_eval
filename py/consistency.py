"""Measure how often the agent gives the same answer to the same question.

This is the study's lead question, and on this dataset it can be answered without
a grader. Every ground truth in the three chosen capsules is numeric -- counts,
ratios, p-values, percentages -- so agreement between replicates is a comparison
of parsed numbers rather than an LLM judgment. The grader noise characterized in
Phase 0 therefore cannot touch the headline figure.

Agreement is reported at three tolerances because exact string equality is the
wrong test: an agent answering "1.33" on one run and "1.3307" on the next has not
contradicted itself, while one answering 260 and then 680 has.

Trajectories that hit the step ceiling or submitted nothing are excluded and
counted separately. Pooling them would let budget exhaustion masquerade as
disagreement, which is precisely the artifact this study exists to separate out.

Usage:
    python py/consistency.py --runs results/agent_runs.csv \
        --out results/consistency.csv
"""

import argparse
import collections
import csv
import itertools
import re
import statistics
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Matches integers, decimals and scientific notation, with optional sign and
# thousands separators. Ordered so the exponent is consumed when present.
NUM_RE = re.compile(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?(?:[eE][-+]?\d+)?"
                    r"|[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_number(text):
    """Pull the agent's submitted value out of a free-text answer.

    The first number in the answer is taken. Agents here lead with the value and
    then explain it -- "1.3307 (or 680:511, approximately 1.33:1)", "260 genes
    show significant hypermethylation" -- so the first number is the submission
    and the rest is commentary. Returns None when nothing parses, which is itself
    recorded rather than silently dropped.
    """
    if not text:
        return None
    # The submission is wrapped in tags; strip them before reading.
    body = re.sub(r"</?answer>", " ", text)
    m = NUM_RE.search(body)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def agree(a, b, tol):
    """Whether two parsed answers match within a relative tolerance.

    Relative rather than absolute, because the answers span p-values near 1e-194
    and counts in the thousands; a fixed epsilon would be meaningless across that
    range. Zero is handled exactly, since a relative test is undefined there.
    """
    if a is None or b is None:
        return False
    if tol == 0:
        return a == b
    if a == 0 or b == 0:
        return a == b
    return abs(a - b) / max(abs(a), abs(b)) <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", default="results/agent_runs.csv")
    ap.add_argument("--out", default="results/consistency.csv")
    ap.add_argument("--capsules", nargs="+", default=["bix-8", "bix-49", "bix-26"])
    args = ap.parse_args()

    rows = [r for r in csv.DictReader((REPO / args.runs).open())
            if r["capsule"] in args.capsules]

    by_q = collections.defaultdict(list)
    excluded = collections.Counter()
    for r in rows:
        # Exclusions come first: a truncated or empty trajectory is not evidence
        # about what the agent thinks the answer is.
        if r["hit_ceiling"] == "True":
            excluded["hit_ceiling"] += 1
            continue
        if r["has_answer"] == "False":
            excluded["empty_answer"] += 1
            continue
        val = parse_number(r["agent_answer"])
        if val is None:
            excluded["unparseable"] += 1
            continue
        by_q[(r["capsule"], r["question_id"])].append(val)

    out_rows = []
    for (cap, qid), vals in sorted(by_q.items()):
        n = len(vals)
        pairs = list(itertools.combinations(vals, 2))
        rec = {"capsule": cap, "question_id": qid, "n_usable_replicates": n,
               "n_pairs": len(pairs)}
        for tol, name in [(0, "exact"), (0.01, "within_1pct"), (0.05, "within_5pct")]:
            rec[f"agree_{name}"] = (
                round(sum(agree(a, b, tol) for a, b in pairs) / len(pairs), 4)
                if pairs else ""
            )
        # Distinct values and modal share summarize the spread without needing a
        # pairwise view: 1 distinct value means perfect stability.
        counts = collections.Counter(vals)
        rec["n_distinct"] = len(counts)
        rec["modal_share"] = round(counts.most_common(1)[0][1] / n, 4) if n else ""
        rec["median_answer"] = statistics.median(vals) if vals else ""
        rec["min_answer"] = min(vals) if vals else ""
        rec["max_answer"] = max(vals) if vals else ""
        out_rows.append(rec)

    if not out_rows:
        raise SystemExit("no usable trajectories yet")

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0]))
        w.writeheader()
        w.writerows(out_rows)

    print(f"wrote {out} ({len(out_rows)} questions)")
    if excluded:
        print("excluded:", dict(excluded))
    print(f"\n{'question':12s} {'n':>2s} {'exact':>6s} {'<=1%':>6s} {'<=5%':>6s} "
          f"{'distinct':>8s} {'modal':>6s}  range")
    def fmt(v):
        """Blank rather than 0.00 when a question has too few replicates to pair."""
        return f"{v:6.2f}" if isinstance(v, (int, float)) else f"{'-':>6s}"

    for r in out_rows:
        print(f"{r['question_id']:12s} {r['n_usable_replicates']:2d} "
              f"{fmt(r['agree_exact'])} {fmt(r['agree_within_1pct'])} "
              f"{fmt(r['agree_within_5pct'])} {r['n_distinct']:8d} "
              f"{fmt(r['modal_share'])}  {r['min_answer']:g} .. {r['max_answer']:g}")

    # Pooled figures, weighted by pairs so questions with more usable replicates
    # count for more.
    tp = sum(r["n_pairs"] for r in out_rows)
    if tp:
        print()
        for name in ("exact", "within_1pct", "within_5pct"):
            pooled = sum(r[f"agree_{name}"] * r["n_pairs"]
                         for r in out_rows if r["n_pairs"]) / tp
            print(f"pooled agreement ({name}): {pooled:.1%}  over {tp} pairs")


if __name__ == "__main__":
    main()
