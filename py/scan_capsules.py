"""Profile BixBench capsules from the dataset's own metadata.

Supersedes an earlier keyword scan over question text. `BixBench.jsonl` on
Hugging Face carries a curator-assigned `categories` field per question, so
subject matter can be read directly instead of guessed at.

Two jobs:

  1. Group questions into capsules and report their curator categories, so the
     failure-taxonomy phase can be pointed at a domain-relevant cluster.
  2. Record which verifier grades each question. Only `llm_verifier` questions
     are exposed to grader sampling noise; `str_verifier` and `range_verifier`
     are deterministic comparisons. That split is what lets agent noise be
     separated from grader noise, so it drives capsule selection as much as
     subject matter does.

The dataset is public (not gated, despite the README), but an `hf auth login`
token avoids rate limits.

Usage:
    python py/scan_capsules.py --out results/capsule_profile.csv
"""

import argparse
import ast
import collections
import csv
import json
from pathlib import Path

from huggingface_hub import hf_hub_download

REPO_ID = "futurehouse/BixBench"
METADATA_FILE = "BixBench.jsonl"

# Categories that mark the RNA-seq / differential-expression cluster. This is
# the taxonomy target: BixBench has no microbiome or metagenomics capsules
# (see env/SETUP.md), so the next-closest domain is the one to work in.
RNASEQ_CLUSTER = {"RNA-seq", "Differential Expression Analysis", "Transcriptomics"}


def parse_categories(raw):
    """Split the `categories` field, which upstream stores two different ways.

    Most records hold a plain comma-separated string. 57 of 205 instead hold the
    repr of a Python list, e.g. "['Genomics', 'Phylogenetics']". Splitting on
    commas alone shreds that second form into fragments like "['Genomics'" --
    a silent corruption that produces plausible-looking but wrong category
    counts, so both forms are handled explicitly.
    """
    raw = (raw or "").strip()
    if raw.startswith("["):
        try:
            return [str(x).strip() for x in ast.literal_eval(raw) if str(x).strip()]
        except (ValueError, SyntaxError):
            pass  # fall through to comma-splitting
    return [p.strip() for p in raw.split(",") if p.strip()]


def load_metadata():
    """Fetch just the metadata file; the 64 capsule zips are not needed here."""
    path = hf_hub_download(REPO_ID, METADATA_FILE, repo_type="dataset")
    with open(path) as fh:
        return [json.loads(line) for line in fh]


def build_profile(rows):
    """Collapse one-row-per-question into one-row-per-capsule."""
    caps = collections.defaultdict(
        lambda: {
            "n": 0,
            "modes": collections.Counter(),
            "cats": set(),
            "paper": None,
            "uuid": None,
        }
    )
    for r in rows:
        c = caps[r["short_id"]]
        c["n"] += 1
        c["modes"][r["eval_mode"]] += 1
        c["cats"].update(parse_categories(r["categories"]))
        c["paper"] = r["paper"]
        c["uuid"] = r["capsule_uuid"]
    return caps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/capsule_profile.csv")
    args = ap.parse_args()

    rows = load_metadata()
    caps = build_profile(rows)

    modes = collections.Counter(r["eval_mode"] for r in rows)
    print(f"{len(rows)} questions across {len(caps)} capsules")
    print("verifier split:", dict(modes))
    print(f"LLM-graded (noise-exposed): {modes['llm_verifier'] / len(rows):.1%}")

    # Category totals. Worth printing in full: the absence of a microbiome or
    # metagenomics category is itself a finding, and only visible in the whole list.
    cat_counts = collections.Counter()
    for c in caps.values():
        cat_counts.update(c["cats"])
    print(f"\ncurator categories across {len(caps)} capsules:")
    for cat, n in cat_counts.most_common():
        print(f"  {n:3d}  {cat}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "capsule", "capsule_uuid", "n_questions",
                "n_llm_verifier", "n_str_verifier", "n_range_verifier",
                "in_rnaseq_cluster", "categories", "paper",
            ]
        )
        for cap in sorted(caps, key=lambda s: int(s.split("-")[1])):
            c = caps[cap]
            w.writerow([
                cap, c["uuid"], c["n"],
                c["modes"]["llm_verifier"],
                c["modes"]["str_verifier"],
                c["modes"]["range_verifier"],
                bool(c["cats"] & RNASEQ_CLUSTER),
                ";".join(sorted(c["cats"])),
                c["paper"],
            ])
    print(f"\nwrote {out}")

    cluster = [k for k, v in caps.items() if v["cats"] & RNASEQ_CLUSTER]
    print(f"RNA-seq cluster: {len(cluster)} capsules, "
          f"{sum(caps[k]['n'] for k in cluster)} questions")


if __name__ == "__main__":
    main()
