"""Rank capsules by how likely they are to run cheaply and finish inside the step budget.

Motivation: the first three capsules run cost $1.35, $3.22 and $2.86 per replica,
and the two expensive ones truncated at the step ceiling. Data size turned out not
to explain that -- the cheapest capsule holds more data than one of the expensive
ones. Mean question length does track it, which fits the mechanism: a question
that spells out a multi-stage pipeline demands more agent actions, and every
action carries the full notebook context.

The ranking is a screening tool, not a model. It is fitted to three observations,
so it orders candidates for a cheap pilot rather than replacing one.

Usage:
    python py/predict_cost.py --top 20
"""

import argparse
import ast
import collections
import csv
import json
import re
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "futurehouse/BixBench"

# Command-line pipelines the execution image does not ship. A capsule demanding
# these is not merely expensive, it may be unrunnable -- the lesson from bix-61,
# whose questions require Trimmomatic, BWA and GATK, none of which are installed.
# Verified against the image rather than assumed: phykit 2.0.1, biopython and
# ete3 are all present, so phylogenetics capsules built on them are runnable and
# are deliberately not penalized here. What is absent is the read-processing and
# variant-calling stack -- trimmomatic, bwa, gatk, samtools, bcftools -- which is
# what makes bix-61 unrunnable.
HEAVY_TOOLS = (
    r"trimmomatic|bwa|gatk|samtools|bcftools|bowtie|minimap|picard|vcftools|"
    r"hisat|salmon|kallisto|star aligner|fastq|alignment|variant call|assembl|"
    r"haplotype|sra|srr\d"
)

# Measured anchors, cost per replica at max_steps 20.
MEASURED = {"bix-8": 1.3525, "bix-43": 3.2203, "bix-53": 2.8571}


def parse_categories(raw):
    raw = (raw or "").strip()
    if raw.startswith("["):
        try:
            return [str(x).strip() for x in ast.literal_eval(raw) if str(x).strip()]
        except (ValueError, SyntaxError):
            pass
    return [p.strip() for p in raw.split(",") if p.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=20)
    ap.add_argument("--out", default="results/capsule_cost_ranking.csv")
    args = ap.parse_args()

    path = hf_hub_download(REPO_ID, "BixBench.jsonl", repo_type="dataset")
    rows = [json.loads(line) for line in open(path)]

    caps = collections.defaultdict(
        lambda: {"qs": [], "cats": set(), "heavy": 0}
    )
    for r in rows:
        c = caps[r["short_id"]]
        c["qs"].append(r["question"])
        c["cats"].update(parse_categories(r["categories"]))
        if re.search(HEAVY_TOOLS, r["question"], re.I):
            c["heavy"] += 1

    ranked = []
    for sid, c in caps.items():
        mean_len = sum(map(len, c["qs"])) // len(c["qs"])
        ranked.append({
            "capsule": sid,
            "n_questions": len(c["qs"]),
            "mean_question_chars": mean_len,
            "questions_naming_missing_tools": c["heavy"],
            "measured_cost_per_replica": MEASURED.get(sid, ""),
            "categories": ";".join(sorted(c["cats"])),
        })

    # Cheapest-looking first; capsules naming absent toolchains are pushed down
    # regardless of length, since those risk failing outright rather than costing more.
    ranked.sort(key=lambda r: (r["questions_naming_missing_tools"] > 0,
                               r["mean_question_chars"]))

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(ranked[0]))
        w.writeheader()
        w.writerows(ranked)

    print(f"{'capsule':9s} {'n':>2s} {'chars':>6s} {'tools':>5s} {'measured':>9s}  categories")
    for r in ranked[: args.top]:
        m = f"${r['measured_cost_per_replica']:.2f}" if r["measured_cost_per_replica"] else ""
        print(f"{r['capsule']:9s} {r['n_questions']:2d} {r['mean_question_chars']:6d} "
              f"{r['questions_naming_missing_tools']:5d} {m:>9s}  {r['categories'][:52]}")
    print(f"\nwrote {out}")
    print("anchors: bix-8 132 chars -> $1.35 (no truncation); "
          "bix-43 289 -> $3.22 and bix-53 365 -> $2.86 (both truncated)")


if __name__ == "__main__":
    main()
