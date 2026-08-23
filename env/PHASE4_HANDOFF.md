# Phase 4 handoff — failure review

Reviewed by reading the agent notebooks against the capsule ground truth. Each row
carries a diagnosis and a confidence level. **Rows marked Low or Medium need your
domain judgment**; rows marked High are, I think, settled.

Data: `results/agent_runs.csv` (159 trajectories), notebooks embedded in the
trajectory JSONs under
`../BixBench-upstream/data/trajectories/pricing_bix8/pricing_bix8_claude45/`.
Extract any of them with `python py/collect_trajectories.py --run
pricing_bix8_claude45 --write-notebooks`.

## The headline of this review

**Three of the six wrong answers I examined are not agent errors.** In each case
the agent computed the ground-truth number, printed it, and then deliberately
replaced it with a more defensible one. The benchmark scores that as failure.

## Review table

| # | Question | Ideal | Agent | Diagnosis | Category | Confidence |
|---|---|---|---|---|---|---|
| 1 | `bix-8-q6` | 680 | **260** (10/10 identical) | Question asks "how many **genes**". Data is transcript-level (`ENST…`) with a `gene_id` column. The agent found 680 hypermethylated **transcripts** — printed it explicitly — then deduplicated to **260 unique genes** and answered that. Ground truth is the transcript count. | **Benchmark ground-truth error** — question says genes, answer counts transcripts | **High** |
| 2 | `bix-8-q7` | 106 | **70** | Identical mechanism. Agent computed 106 transcript entries with `m6A Hyper AND Up`, verified it two ways, then reported 70 unique `gene_id`s. | **Benchmark ground-truth error** — same transcript/gene conflation | **High** |
| 3 | `bix-8-q5` | `p < 2.2e-16` | **8.100776e-194** | Chi-square on the m6A × DEG contingency table; χ²=901.4, df=4. `2.2e-16` is R's *display floor* — what `print()` emits below machine epsilon — not a value. scipy reports the true p. **8.1e-194 is < 2.2e-16, so the agent is correct and more precise.** | **Benchmark ground-truth error** — R print artifact recorded as truth | **High** |
| 4 | `bix-49-q4` | 2118 | **1754** (up 1096, down 658) | Count matrix has 21 samples; metadata has 19. Agent dropped the 2 unmatched samples and ran DESeq2 on 19. Fewer samples → less power → fewer DEGs, and the deficit is much larger among down-regulated genes (658 vs an implied 952). Plausible but unproven: the capsule author used a different sample set or pre-filter. | Sample-inclusion / pre-filtering difference | **Medium** |
| 5 | `bix-49-q3` | 1166 | **1096** | Same DESeq2 run as #4; this is the up-regulated subset. Stands or falls with #4. | Same root cause as #4 | **Medium** |
| 6 | `bix-49-q1` | 4.80 | **5.15** | Max log2FC among significant upregulated genes, after apeglm shrinkage. A larger maximum from a *smaller* significant set is odd and does not follow from #4 alone — suggests the shrinkage step or the significance filter differs, not just the sample set. | Unresolved; possibly apeglm parameterization | **Low** |
| 7 | `bix-49-q2` | 7.04E-26 | **8.76e-25** | Adjusted p-value for a single named gene, GRIK5. Off by ~12×. A single gene's padj depends on the whole multiple-testing set, so this is consistent with #4's different gene universe — but 12× is large. | Unresolved; likely downstream of #4 | **Low** |
| 8 | `bix-26-q5` | 3 | **1** (range 1–58 across replicates) | Pathways enriched under iron-depletion but not innate media, with \|log2FC\|>1.5 and padj<0.05. Agent built both pathway lists and took the difference. Four distinct answers across replicates means the enrichment step itself is unstable, not just the final comparison. | Genuine agent instability, plus possible threshold ambiguity | **Low** |
| 9 | `bix-26-q4` rep 9 | — | *no answer* | The only truncation in the campaign: 40 of 40 actions. Distinct from the nine Bioconductor deaths. | Budget exhaustion | **High** |

## What I did not review, and why

The other **nine non-responses** are one documented mechanism: the agent follows
the harness's own `R_SPECIFIC_GUIDELINES` install idiom, the image lacks
`BiocManager`, and the run dies at 6–17 of 40 actions. Reading more of them adds
nothing. See `env/SETUP.md`.

Questions at 90–100% graded-correct — `bix-8-q1/q2/q3`, `bix-26-q3`, `bix-49-q5` —
were skipped as uninformative.

## Suggested taxonomy, revised from what is actually here

The original brief's categories assumed the agent would fail by doing bad
analysis. Mostly it does not. What the notebooks show:

1. **Benchmark ground-truth error** (#1, #2, #3) — the agent is right and is
   scored wrong. Two flavors: an entity-level mismatch between question and answer
   key (transcripts vs genes), and a tooling artifact frozen into the answer key
   (R's `2.2e-16` display floor).
2. **Silent cohort divergence** (#4, #5) — a defensible data-cleaning choice
   (dropping samples absent from the metadata) propagates into every downstream
   count. No error message, no flag; only the number moves.
3. **Unstable intermediate step** (#8) — the enrichment analysis itself varies run
   to run, so the final count varies 1–58.
4. **Self-inflicted environment failure** (the nine) — following the harness's own
   documented idiom kills the run.
5. **Budget exhaustion** (#9).

Categories 1 and 4 are properties of the benchmark, not the agent. That is the
uncomfortable and interesting result: **on this sample, more of the scored
failures trace to BixBench than to the model.**

## What I need from you

- **#4/#5**: is dropping the 2 metadata-less samples the right call, and would it
  produce a shortfall this size? Do you read 658 vs ~952 down-regulated as a power
  effect or as something else?
- **#6**: can a larger max log2FC coexist with a smaller significant set under
  apeglm, or does that imply a different shrinkage call?
- **#7**: is a 12× shift in one gene's padj plausible from a different gene
  universe alone?
- **#8**: is the |log2FC|>1.5 threshold on a *pathway mean* well defined? The
  agent averaged per-pathway log2FC; a different aggregation would change the count.
