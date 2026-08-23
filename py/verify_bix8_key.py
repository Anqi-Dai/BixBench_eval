"""Recompute every bix-8 answer directly from the capsule spreadsheet.

The MeRIP file is transcript-level (one row per ENST id) with a gene_id
column, so each question has two candidate answers: a row count and a
unique-gene count. This script prints both, plus the chi-square test the
q2/q5 answer key implies, so the review table's diagnoses rest on numbers
that were actually recomputed rather than read off the agent notebooks.

Run with any Python that has pandas, scipy and openpyxl:
    python py/verify_bix8_key.py path/to/CapsuleFolder-48a6b469-*/MeRIP_RNA_result.xlsx
"""

import sys

import pandas as pd
from scipy.stats import chi2_contingency

df = pd.read_excel(sys.argv[1])

# The dataset's category labels, used by every question in the capsule.
hyper = df[df.m6A == "m6A Hyper"]
hypo = df[df.m6A == "m6A Hypo"]
hyper_up = df[(df.m6A == "m6A Hyper") & (df.DEG == "Up")]

# q6 — "how many genes show significant hypermethylation".
# The ideal answer (680) is the transcript-row count; the agent's 260 is the
# unique-gene count, which is what the question's wording asks for.
print("q6  transcripts:", len(hyper), "| unique genes:", hyper.gene_id.nunique())

# q7 — same entity conflation: ideal 106 rows vs 70 unique genes.
print("q7  transcripts:", len(hyper_up), "| unique genes:", hyper_up.gene_id.nunique())

# q1 — percent of hypermethylated that are upregulated. The ideal 15.6% is
# the transcript-level fraction, so the key is transcript-level here too.
print("q1  transcript-level: %.2f%% | gene-level: %.2f%%"
      % (100 * len(hyper_up) / len(hyper),
         100 * hyper_up.gene_id.nunique() / hyper.gene_id.nunique()))

# q3 — hyper/hypo ratio. Ideal 1.33 is again the transcript-level value.
# One agent replicate answered 2.064 = 258/125: the gene-level ratio after
# excluding the two genes that carry both hyper and hypo transcripts.
both = (df.groupby("gene_id").m6A
          .agg(lambda s: {"m6A Hyper", "m6A Hypo"} <= set(s)))
n_both = int(both.sum())
print("q3  transcript-level: %.4f | gene-level: %.4f | gene-level excl. %d dual-status genes: %.4f"
      % (len(hyper) / len(hypo),
         hyper.gene_id.nunique() / hypo.gene_id.nunique(), n_both,
         (hyper.gene_id.nunique() - n_both) / (hypo.gene_id.nunique() - n_both)))

# q2/q5 — chi-square of m6A status x DEG status. The full 3x3 table gives
# the chi-square inside the key's range (900.5, 902.5) and the exact p the
# agent reported; "p < 2.2e-16" in the key is R's print floor, not a value.
r3 = chi2_contingency(pd.crosstab(df.m6A, df.DEG))
print("q2/q5  3x3: chi2=%.4f df=%d p=%.6e" % (r3.statistic, r3.dof, r3.pvalue))

# One replicate answered 321.1: the same test after collapsing both factors
# to significant vs not — a defensible alternative reading of "status".
r2 = chi2_contingency(pd.crosstab(df.m6A.isin(["m6A Hyper", "m6A Hypo"]),
                                  df.DEG.isin(["Up", "Down"])))
print("q2 collapsed 2x2: chi2=%.4f p=%.4e" % (r2.statistic, r2.pvalue))
