"""Shortlist BixBench capsules by subject matter, without Hugging Face auth.

The BixBench repo ships zero-shot baseline CSVs that already carry one row per
question: the question text, a model answer, the ground-truth target, and which
verifier graded it. That is enough to do two Phase 0 jobs for free -- no gated
dataset download and no API spend:

  1. Sort capsules by subject, so the failure-taxonomy phase can be pointed at
     the ones closest to the reviewer's own domain.
  2. Count how many questions are graded by an LLM rather than by a
     deterministic string or range comparison. Only the LLM-graded ones are
     exposed to grader sampling noise, which is the main threat to the
     reliability finding.

Usage:
    python py/scan_capsule_subjects.py --baseline <path/to/*-grader-openended.csv>
"""

import argparse
import collections
import csv
import re
from pathlib import Path

# Crude keyword patterns over question text. This is a shortlisting tool, not a
# classifier: it is meant to cut 53 capsules down to a readable handful, and
# every hit still gets confirmed by reading the capsule.
TOPICS = {
    "microbiome_metagenomics": r"microbiom|metagenom|16S|amplicon|taxonom|OTU|ASV|shotgun|kraken|humann|qiime|picrust|shortbred",
    "rnaseq_diffexpr": r"RNA-seq|rnaseq|DESeq|edgeR|limma|differential expression|DEG|counts matrix|TPM|FPKM",
    "enrichment_pathway": r"enrichGO|GO enrichment|KEGG|GSEA|pathway|clusterProfiler",
    "single_cell": r"single-cell|scRNA|Seurat|scanpy|UMAP",
    "variant_genomics": r"variant|VCF|SNP|mutation|GWAS|allele",
    "clinical_survival": r"surviv|Kaplan|Cox|hazard|clinical outcome|cohort",
    "imaging": r"image|microscop|segmentation|pixel",
}

# Capsule ids are the question-uuid prefix. Upstream capitalization is
# inconsistent (both "bix-33-q6" and "Bix-33-q6" appear), so the pattern is
# case-insensitive -- matching case-sensitively would silently drop rows.
UUID_RE = re.compile(r"[Bb]ix-(\d+)-q\d+$")


def load(path):
    """Read a baseline CSV and attach a normalized capsule id to each row."""
    rows = list(csv.DictReader(Path(path).open()))
    for r in rows:
        m = UUID_RE.match(r["uuid"])
        if m is None:
            raise ValueError(f"unrecognized question uuid: {r['uuid']!r}")
        r["capsule"] = f"bix-{m.group(1)}"
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", required=True, help="zero-shot baseline CSV")
    ap.add_argument("--out", default="results/capsule_subject_scan.csv")
    args = ap.parse_args()

    rows = load(args.baseline)

    # Which verifier grades each question, across the whole set. The
    # llm_verifier share is the fraction of the benchmark where grader noise is
    # even possible.
    modes = collections.Counter(r["evaluation_mode"] for r in rows)
    print(f"{len(rows)} questions across {len({r['capsule'] for r in rows})} capsules")
    print("verifier split:", dict(modes))
    llm_share = modes.get("llm_verifier", 0) / len(rows)
    print(f"LLM-graded share: {llm_share:.1%}\n")

    # Per capsule: how many questions, how many are LLM-graded, and which
    # topics its question text touches.
    per_capsule = collections.defaultdict(
        lambda: {"n": 0, "n_llm": 0, "topics": set()}
    )
    for r in rows:
        c = per_capsule[r["capsule"]]
        c["n"] += 1
        c["n_llm"] += r["evaluation_mode"] == "llm_verifier"
        for topic, pat in TOPICS.items():
            if re.search(pat, r["question"], re.I):
                c["topics"].add(topic)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["capsule", "n_questions", "n_llm_graded", "topics"])
        for cap in sorted(per_capsule, key=lambda s: int(s.split("-")[1])):
            c = per_capsule[cap]
            w.writerow([cap, c["n"], c["n_llm"], ";".join(sorted(c["topics"]))])
    print(f"wrote {out}")

    # Topic totals, so it is obvious at a glance which domains BixBench actually
    # covers -- including any that turn out to be absent.
    print("\ncapsules per topic:")
    for topic in TOPICS:
        n = sum(topic in c["topics"] for c in per_capsule.values())
        print(f"  {topic:24s} {n:2d}")


if __name__ == "__main__":
    main()
