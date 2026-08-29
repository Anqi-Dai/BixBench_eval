# Failure review, verified by recomputation

This is the case-by-case supplement behind [writeup.md](../writeup.md)'s
Figure 4 and the interactive run audit: every campaign answer that missed the
key by more than 1%, with its measured cause.

Three passes are merged here. The first read the agent notebooks against the
capsule ground truth and assigned provisional diagnoses. The second
(2026-08-23) re-ran every analysis from the raw capsule data inside the
benchmark's own Docker image (`futurehouse/bixbench:aviary-notebook-env`) and
either confirmed each diagnosis exactly or replaced it with the measured
cause. The third (same day) pulled the **capsule authors' original notebooks
from the Hugging Face dataset** — the harness strips them from the data folder
the agent sees — and confirmed the derivation of every answer key in the three
campaign capsules from the authors' own code and cell outputs.

Verification scripts, each with its `docker run` line in the header:
`R/verify_bix49_key.R`, `R/verify_bix26_key.R`, `py/verify_bix8_key.py`
(campaign capsules); `R/verify_bix1_key.R`, `R/verify_bix43_key.R` (pilot
capsules, excluded from the table below — see the scope note).

Data: `results/agent_runs.csv` (159 trajectories: 140 campaign + 19 pilot),
agent notebooks embedded in the trajectory JSONs (~216 MB, not tracked in
this repo; deposited with the Zenodo archive), author notebooks inside the `CapsuleFolder-*.zip` files on
`huggingface.co/datasets/futurehouse/BixBench`.

## Scope: K=10 campaign capsules only

The review table covers **bix-8, bix-49 and bix-26** — the three capsules with
the full K=10 replicate campaign. Deviating answers from the K=1 pilot runs
(bix-1, bix-43, bix-4) were verified along the way but are **excluded from the
table and from all counts**: they are single draws, several from runs that hit
the pilot's 20-step ceiling mid-analysis, so they carry no replicate evidence
and mix truncation artifacts with genuine divergence. Decision recorded
2026-08-23. For the record, nothing found there contradicts the table: the
bix-1 key reproduces only under the same undisclosed sex covariate as bix-49
(the author notebook is the same pipeline), bix-43-q3's agent answer (525) is
the exact two-group DESeq2 output while the key's 677 matched no variant
tried, and bix-4's key is underdetermined by the shipped data (DVMC needs
trees the capsule doesn't contain and the questions don't specify how to
build). The pilot verification scripts are kept for reference.

**Confidence scale.** GT = ground truth (the answer key). *Documented* = the cause is read directly from the
capsule author's own notebook code or cell output, and recomputation matches.
*Verified* = key and agent numbers both reproduced digit-for-digit, cause
therefore measured. Every row in the table sits at one of these two levels;
the first pass's Low/Medium/High judgment ratings are fully retired.

## The headline

**On the questions examined, most scored failures trace to the benchmark, not
the model — and none trace to badly executed statistics.** This is no longer
an inference: for every campaign-capsule answer key that any agent replicate
missed by more than 1%, the author notebooks show how the key was derived, and
in the majority of rows the defect sits in the key or the question, not in the
agent's analysis.

## Review table — campaign questions with any answer >1% from the key

"Agent" is the modal answer unless a replicate is named.

| # | Question | Key | Agent | Exact cause (measured) | Category | Confidence |
|---|---|---|---|---|---|---|
| 1 | `bix-8-q6` | 680 | **260** (10/10) | Key counts transcript rows: the author's notebook derives it as `count(m6A)` on the ENST-level table (680 rows = 260 unique genes) with no deduplication anywhere in the notebook; the question asks for *genes*. Agent deduplicated correctly. | GT error — entity conflation | **Documented** |
| 2 | `bix-8-q7` | 106 | **70** | Same derivation: the author's `count(m6A_DEG)` output shows "m6A Hyper and Up 106" at transcript level; 106 rows = 70 unique genes. | GT error — entity conflation | **Documented** |
| 3 | `bix-8-q5` | `p < 2.2e-16` | **8.100776e-194** | The author's output cell reads verbatim `X-squared = 901.45, df = 4, p-value < 2.2e-16` — the key copies R's console print floor; the actual p was never extracted. Recomputed: p = 8.100776e-194, matching the agent to the last digit. | GT error — tooling artifact | **Documented** |
| 4 | `bix-8-q2` rep 0 | (900.5, 902.5) | **321.1047** | Exactly the same test after collapsing both factors to significant-vs-not (2×2). A defensible reading of "status"; 9/10 replicates chose the author's 3×3. *Ruled question ambiguity (decision 2026-08-24): binarize-then-test is standard practice and the question never precludes it — one phrase ("use all levels") would.* | Question ambiguity → answer variability | **Verified** |
| 5 | `bix-8-q3` rep 2 | 1.33 | **2.064** | The question asks for a ratio of *genes*; the key's 1.33 is the transcript-row ratio (680/511 ENST rows). This replicate aggregated to gene level (260 hyper / 127 hypo unique `gene_id`s), discovered **2 genes carrying both hyper and hypo transcripts** — unclassifiable under the question's binary framing — documented three handling options in its notebook, and conservatively excluded them: 258/125 = 2.0640, reproduced exactly. A more rigorous answer to the question as worded than the key, scored wrong. (The naive gene-level ratio is 2.05, so *any* gene-level reading fails against the transcript-level key.) | GT error — entity conflation | **Verified** |
| 6 | `bix-49-q4` | 2118 | **1754** | The author's notebook: `design = ~sex+condition`. The key (2118) reproduces exactly under it; the agent's 1754 is exact under `~condition`. **No question mentions sex.** Sample handling is identical on both sides — the author also drops MGD1640B/MGD1641B, for reasons stated only in the stripped notebook ("alcohol use disorder", "taking valproic acid"). The first pass's "sample-inclusion" diagnosis is withdrawn. | GT error — hidden analysis spec | **Documented** |
| 7 | `bix-49-q3` | 1166 | **1096** | Same run: 1166 under the sex-adjusted design, 1096 under the agent's. | GT error — hidden analysis spec | **Documented** |
| 8 | `bix-49-q1` | 4.80 | **5.15** | Two compounding causes: the key is the padj-based max under `~sex+condition` (4.8028); the agent took q1's literal "significant (p<0.05)" as raw p under its design (5.1467). Nothing to do with apeglm settings. | GT hidden spec + question ambiguity | **Documented** |
| 9 | `bix-49-q2` | 7.04E-26 | **8.76e-25** | GRIK5 padj: 7.0400e-26 under the sex design, 8.7632e-25 under the agent's. The 12× gap is the design formula, not the gene universe. | GT error — hidden analysis spec | **Documented** |
| 10 | `bix-49-q5` | 3.83 | **3.87** (9/9) | GRIK5 LFC: 3.8255 vs 3.8737 under the two designs. This is the question the two graders split on 9/9 vs 9/9 — not a rounding-tolerance issue; the two numbers are different analyses. | GT error — hidden analysis spec | **Documented** |
| 11 | `bix-26-q5` | 3 | **1** (modal; 1–58) | The author's notebook filters DEGs by **fold change only — the padj < 0.05 the question states is never applied** — enriches up/down separately, and then **never computes the set difference in code**: the notebook ends at a dotplot, so the key was read off the plot. That exact pipeline reproduces the key today (3: pau02024, pau00460, pau00643). Under the question's stated thresholds the answer is 1 — the agent's modal answer. The replicate scatter: four replicates answering 58 misread the gene-level DESeq2 files as pathway tables and never ran enrichment — *ruled plain agent error (decision 2026-08-24): the column signature (`baseMean`, `lfcSE`, `stat`, locus-tag ids) is unmistakably gene-level and 6/10 replicates recognized it, so the question's confused wording does not excuse it*. The 12-replicate hit the wording contradiction explicitly and switched to GSEA NES — that one stays wording-driven. Replicate 9 (answer 2) *invented* a pathway-level fold-change metric to satisfy the wording — ruled agent error (decision 2026-08-28): fabricating a metric is the agent's choice; the correct behavior is to flag that the question asks for one that standard over-representation analysis (ORA) cannot supply. | GT error — key contradicts stated thresholds, + agent error (the 58s; rep 9's invented metric) | **Documented** |
| 12 | `bix-26-q4` reps 0, 5 | 5 | 7, 33 | The key reproduces exactly (5 common down-pathways) under both the stated thresholds and the author's own pipeline, and 5/7 answering replicates match it. The two outliers are genuine agent errors. | Agent error / instability | **Verified** |
| 13 | `bix-26-q4` rep 9 | — | *no answer* | The only truncation in the campaign: 40 of 40 actions. Distinct from the nine Bioconductor deaths. | Budget exhaustion | **Verified** |

**Also verified in passing:** the bix-8 answer key is transcript-level
*throughout* — q1's 15.6% and q3's 1.33 are row-level values too, so the agent
was scored correct on those two only because it happened to answer at row
level; `bix-26-q3` (11) reproduces exactly under both the stated thresholds
and the author's pipeline, validating the KEGG reading used in rows 11–12.

## One question, ten notebooks (bix-26-q5)

The Phase 4 question "does the agent fail the same way each time?" was
answered by classifying the analytical route in all ten replicate notebooks
for the least stable question. It does not: the replicates split across
**four distinct routes**, and the answer is determined by the route, not by
noise within one.

| Route | Replicates | Answer |
|---|---|---|
| Canonical ORA (`enrichKEGG`, stated thresholds) | 0, 2, 4 | 1 |
| Gene tables misread as pathway tables — no enrichment run | 1, 6, 7, 8 | 58 |
| GSEA (`gseKEGG`), \|NES\| > 1.5 as the "fold change" | 5 | 12 |
| Hand-rolled ORA: own gene→pathway mapping, BH correction, and a constructed pathway-level "log fold change" to satisfy the question's wording | 9 | 2 |
| Bioconductor install death | 3 | — |

Two of the four routes are attempts to make sense of the question's
impossible significance definition; the 58s and replicate 9 are ruled agent
error (see row 11). Replicate 9 is still the most telling notebook: it
understood the data correctly and *invented a pathway fold-change metric*
because the question demanded one that standard ORA cannot supply — but
inventing a metric, rather than flagging the impossibility, is the agent's
own choice (decision 2026-08-28).

## What the author notebooks add

Pulled from the Hub zips (`CapsuleNotebook-*_executed.ipynb`); the harness
ships the agent only the `CapsuleData-*` half, so none of this context was
available to the agent — or to the graders.

- **bix-49 / bix-1**: `design = ~sex+condition` is right there in the code,
  with the comment "control for sample sex". The two extra count-matrix
  samples are removed with documented clinical reasons (alcohol use disorder;
  valproic acid) that exist nowhere in the shipped data. The agent
  independently made the same exclusion for a different reason (no metadata)
  — the right call, unknowable from the question.
- **bix-8**: the entire notebook works at transcript level; a cell even
  inspects ENO1's three transcript rows without noting the implication. The
  chi-square key is a verbatim console print (`p-value < 2.2e-16`).
- **bix-26**: the DEG filter omits the padj threshold the questions state,
  enrichment runs per direction, and no cell computes any of the three
  question answers — they were read off the final dotplot by eye. All three
  keys still reproduce today under that exact pipeline, so KEGG drift has
  (so far) not moved this capsule's answers.

## Error categories, final

1. **Ground-truth error — entity conflation** (rows 1, 2, 5): the key counts
   transcripts where the question says genes, systematically across bix-8.
2. **Ground-truth error — tooling artifact** (row 3): R's `2.2e-16` print
   floor frozen into the answer key.
3. **Ground-truth error — hidden analysis specification** (rows 6–10): the
   key encodes an unstated sex covariate documented only in the author's
   stripped notebook. Ruling (2026-08-24): the sex-adjusted model is the
   correct analysis — the fix is question-side, stating the required design
   ("adjusting for sex, `~sex + condition`") in every affected question.
4. **Ground-truth error — key contradicts the question's stated procedure**
   (row 11): the key's pipeline skips the padj filter the question defines,
   and the question defines pathway significance by a fold change ORA
   pathways don't have.
5. **Question ambiguity → answer variability** (row 4; row 8 in part; row
   11's GSEA replicate): multiple defensible readings, replicates split
   across them. Each is fixable with one phrase in the question ("use all
   levels"; "padj-significant"; a pathway-significance definition ORA can
   actually satisfy).
6. **Genuine agent error / instability** (row 12; row 11's four 58-answer
   replicates and its invented-metric replicate 9): wrong pipeline, unstable
   intermediate step, or a fabricated metric. The 58s are ruled unexcused
   (2026-08-24) — the files' DESeq2 column signature is unmistakably
   gene-level, and 6 of 10 replicates read it correctly; replicate 9 is
   ruled agent error (2026-08-28) — see the rulings log below.
7. **Self-inflicted environment failure** (the nine non-responses): the
   harness's own `R_SPECIFIC_GUIDELINES` install idiom meets an image without
   `BiocManager`. See `env/SETUP.md`.
8. **Budget exhaustion** (row 13).

Categories 1–5 and 7 are properties of the benchmark; 6 and 8 are properties
of the agent. That balance — on this sample, most scored failures are the
benchmark's — is the uncomfortable and interesting result, and it is now
documented from the benchmark's own source material rather than argued.

## Reproducibility caveat for the writeup

The bix-8 and bix-49 verifications are fully deterministic (spreadsheet
counts and DESeq2 on fixed inputs). The bix-26 verification queries the
**live KEGG REST service**, which is updated continuously with no public
versioned snapshot — so its exact matches are claims *as of 2026-08-23*.
Provenance closure (the author-pipeline rerun reproducing 11 / 5 / 3) shows
KEGG has not yet drifted for this capsule, but any answer key built on "the
latest KEGG db" (bix-26-q4's own words) has an undeclared shelf life. State
the recomputation date wherever these numbers appear.

## What I did not review, and why

The other **nine non-responses** are one documented mechanism: the agent
follows the harness's own `R_SPECIFIC_GUIDELINES` install idiom, the image
lacks `BiocManager`, and the run dies at 6–17 of 40 actions. Reading more of
them adds nothing. See `env/SETUP.md`.

Questions at 90–100% graded-correct — `bix-8-q1/q2/q3`, `bix-26-q3`,
`bix-49-q5` — were originally skipped as uninformative; the >1% scan pulled
`bix-49-q5` and single replicates of `bix-8-q2/q3` back in (rows 4, 5, 10).

K=1 pilot deviations (bix-1, bix-43, bix-4) are excluded per the scope note
at the top.

## Judgment calls and rulings

The computational and provenance questions are settled; these are the
judgment calls and how each was ruled:

- ~~Decide the framing of the sex covariate~~ — **resolved 2026-08-24** by
  domain review: the sex-adjusted model is the right analysis for this design;
  the defect is entirely in the question text, which should state the required
  model — e.g. "…comparing disease (ASXL1 mutation) vs control, **adjusting
  for sex** (`design = ~sex + condition`)". With that phrase the five bix-49
  keys (and bix-1's) become answerable exactly as written; without it, two
  defensible analysts produce two different exact answers and only one is
  scored correct. Writeup framing: the key is not wrong, the question is
  incomplete.
- **Strongest verbatim exhibits.**
  the author's `p-value < 2.2e-16` output cell next to the agent's
  8.100776e-194; the `design = ~sex+condition` line next to five questions
  that never mention sex; the agent's "Wait — pathways don't have fold
  changes" cell in the bix-26 GSEA replicate.
- ~~Sanity-check two classification calls~~ — **resolved 2026-08-24** by
  domain review: (1) bix-8-q2's 2×2 stays classified as question ambiguity —
  binarizing is standard practice and the question could preclude it by
  stating "use all levels"; (2) the 58-answer replicates on bix-26-q5 are
  reclassified as plain agent error with no wording excuse — the DESeq2
  column signature is diagnostic, and 6/10 replicates read it correctly.
  Rows 4, 11 and categories 5–6 reflect both rulings.
- **Third ruling, 2026-08-28:** bix-26-q5 replicate 9 (the hand-rolled ORA
  with a constructed pathway-level "fold change", answer 2) is reclassified
  from wording-driven to **agent error**: the question's demand for an
  impossible metric does not license fabricating one; the correct move is to
  say so. The GSEA replicate (rep 5, answer 12) stays wording-driven — it
  reached for an existing standard metric rather than inventing one. Agent
  share of incorrect runs becomes 7 of 80.
