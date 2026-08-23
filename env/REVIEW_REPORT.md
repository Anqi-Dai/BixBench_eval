# Phase 4 review report — failure review, verified by recomputation

Two passes are merged here. The first pass read the agent notebooks against the
capsule ground truth and assigned provisional diagnoses. The second pass
(2026-08-23) re-ran every analysis from the raw capsule data inside the
benchmark's own Docker image (`futurehouse/bixbench:aviary-notebook-env`) and
either confirmed each diagnosis exactly or replaced it with the measured cause.
Scripts, each with its `docker run` line in the header: `R/verify_bix49_key.R`,
`R/verify_bix26_key.R`, `R/verify_bix1_key.R`, `R/verify_bix43_key.R`,
`py/verify_bix8_key.py`.

Data: `results/agent_runs.csv` (159 trajectories), notebooks embedded in the
trajectory JSONs under
`../BixBench-upstream/data/trajectories/pricing_bix8/pricing_bix8_claude45/`.

**Confidence scale.** *Verified* = both the answer key's number and the agent's
number were reproduced digit-for-digit, so the cause is measured, not inferred.
*High* = the mechanism is established but an exact match is blocked by a known
moving part (annotation-database drift). *Unresolved* = the agent's number
reproduces but the key's provenance was not found. *Unverifiable* = the key
cannot be recomputed from the shipped data at all.

## The headline

**On the questions examined, most scored failures trace to the benchmark, not
the model — and none trace to badly executed statistics.** Verification
strengthened the first pass's headline: the three rows already called
"benchmark ground-truth error" were confirmed exactly, and the four rows the
first pass left unresolved collapsed into a single additional ground-truth
defect (a hidden covariate in the author's analysis), not agent error.

## Review table — all questions with any answer >1% from the key

K=10 campaign rows first, then the deviating K=1 pilot rows. "Agent" is the
modal answer unless a replicate is named.

| # | Question | Key | Agent | Exact cause (measured) | Category | Confidence |
|---|---|---|---|---|---|---|
| 1 | `bix-8-q6` | 680 | **260** (10/10) | Key counts transcript rows (680 ENST rows = 260 unique genes); question asks for *genes*. Agent deduplicated correctly. | GT error — entity conflation | **Verified** |
| 2 | `bix-8-q7` | 106 | **70** | Same conflation: 106 Hyper∩Up rows = 70 unique genes. | GT error — entity conflation | **Verified** |
| 3 | `bix-8-q5` | `p < 2.2e-16` | **8.100776e-194** | χ² on the 3×3 table = 901.445, df=4, p = 8.100776e-194 — the agent's answer to the last digit. The key froze R's display floor as if it were a value. | GT error — tooling artifact | **Verified** |
| 4 | `bix-8-q2` rep 0 | (900.5, 902.5) | **321.1047** | Exactly the same test after collapsing both factors to significant-vs-not (2×2). A defensible reading of "status"; 9/10 replicates chose the 3×3. | Question ambiguity → answer variability | **Verified** |
| 5 | `bix-8-q3` rep 2 | 1.33 | **2.064** | Exactly the gene-level ratio after excluding the 2 genes with both hyper and hypo transcripts (258/125). The key's 1.33 is the transcript-row ratio. Arguably the more rigorous answer to "genes". | GT error — entity conflation | **Verified** |
| 6 | `bix-49-q4` | 2118 | **1754** | Key = DESeq2 on the 19 matched samples with `~ sex + condition` (2118 exact). Agent = same 19 samples, `~ condition` (1754 exact). No question mentions sex; the only hint is the coldata filename. Sample handling was identical — the first pass's "sample-inclusion" diagnosis is withdrawn. | GT error — hidden analysis spec | **Verified** |
| 7 | `bix-49-q3` | 1166 | **1096** | Same run: 1166 under the sex-adjusted design, 1096 under the agent's. | GT error — hidden analysis spec | **Verified** |
| 8 | `bix-49-q1` | 4.80 | **5.15** | Two compounding causes: the key is the padj-based max under `~ sex + condition` (4.8028); the agent took q1's literal "significant (p<0.05)" as raw p under its design (5.1467). Nothing to do with apeglm settings. | GT hidden spec + question ambiguity | **Verified** |
| 9 | `bix-49-q2` | 7.04E-26 | **8.76e-25** | GRIK5 padj: 7.0400e-26 under the sex design, 8.7632e-25 under the agent's. The 12× gap is the design formula, not the gene universe. | GT error — hidden analysis spec | **Verified** |
| 10 | `bix-49-q5` | 3.83 | **3.87** (9/9) | GRIK5 LFC: 3.8255 vs 3.8737 under the two designs. This is the question the two graders split on 9/9 vs 9/9 — not a rounding tolerance issue; the two numbers are different analyses. | GT error — hidden analysis spec | **Verified** |
| 11 | `bix-26-q5` | 3 | **1** (modal; 1–58) | Key's 3 reproduces only by reading "significantly enriched" as raw p<0.05 (pau00460/00643/00650), contradicting the question's own "adjusted p-values" definition, under which the answer is 1 — the agent's modal answer. The scatter: four replicates answering 58 treated the gene-level DESeq2 files as pathway tables (invited by the question defining pathway significance via a fold change ORA pathways don't have); the 12-replicate switched to GSEA NES for the same reason. | GT error — self-contradictory definition, + agent instability | **Verified** (KEGG as of 2026-08-23) |
| 12 | `bix-26-q4` reps 0, 5 | 5 | 7, 33 | The key reproduces exactly (5 common down-pathways) and 5/7 answering replicates match it. The two outliers are genuine agent errors. | Agent error / instability | **Verified** (KEGG as of 2026-08-23) |
| 13 | `bix-26-q4` rep 9 | — | *no answer* | The only truncation in the campaign: 40 of 40 actions. Distinct from the nine Bioconductor deaths. | Budget exhaustion | **Verified** |
| 14 | `bix-1-q1` (K=1) | 0.0002 | 0.0013 | Key reproduces (0.0001766 → 0.0002 at the stated 4-dp rounding) **only** under `~ sex + condition` — the same hidden covariate, same ASXL1 data, propagating into GO enrichment. Agent's value sits in the `~condition` family (recomputed 0.0029; GO options account for the wiggle). | GT error — hidden analysis spec | **Verified** for the key; agent approximate |
| 15 | `bix-1-q2` (K=1) | 1.9E-05 | 0.000126 | Under every design tried, "neutrophil activation" is **removed by the `simplify(cutoff=0.7)` step the question itself mandates** — the key records a term a faithful execution deletes. The agent reported its pre-simplify value (recomputed 1.21e-04 under `~condition`) and explicitly flagged the removal. The key's 1.9e-05 lies between the two designs' pre-simplify values (1.2e-04, 1.3e-06); org.Hs.eg.db drift blocks an exact match. | GT error — self-contradictory instruction | **High** |
| 16 | `bix-43-q3` (K=1) | 677 | **525** | Agent's 525 is exactly the two-group DESeq2 `results()` output under the stated thresholds. The key matches no defensible variant tried (apeglm 394, full 30-sample model 992, serum-starved pair 1678). | Key provenance unidentified | **Unresolved** (agent verified) |
| 17 | `bix-43-q2` (K=1) | 6.02 | 5.596 | Odds ratio downstream of the same divergent DEG list as row 16. | Key provenance unidentified | **Unresolved** |
| 18 | `bix-4` q2/q3/q5/q6 (K=1) | various | various | Not recomputable: the capsule ships only protein sequences and BUSCO outputs; DVMC requires gene trees built with an aligner and tree method the questions never specify. The agent still matched q1 (57.43% vs "57%") and q4 (0.2986 vs "0.30"), suggesting pipeline-dependent divergence rather than error. | Key underdetermined by shipped data | **Unverifiable** |

**Also verified in passing:** the bix-8 answer key is transcript-level
*throughout* — q1's 15.6% and q3's 1.33 are row-level values too, so the agent
was scored correct on those two only because it happened to answer at row
level; `bix-26-q3` (11) reproduces the key exactly and validates the KEGG
pipeline reading used for rows 11–12.

## Error categories, final

1. **Ground-truth error — entity conflation** (rows 1, 2, 5): the key counts
   transcripts where the question says genes, systematically across bix-8.
2. **Ground-truth error — tooling artifact** (row 3): R's `2.2e-16` print
   floor frozen into the answer key.
3. **Ground-truth error — hidden analysis specification** (rows 6–10, 14; and
   the raw-p reading in row 11): the key encodes an unstated choice — a sex
   covariate no question mentions, or a significance reading that contradicts
   the question's own definition.
4. **Ground-truth error — self-contradictory instruction** (rows 11, 15): a
   faithful execution of the question's stated procedure cannot produce the
   key (the mandated simplify step deletes the answer term; ORA pathways have
   no fold change to threshold).
5. **Question ambiguity → answer variability** (rows 4, 8 in part, 11 in
   part): multiple defensible readings, replicates split across them.
6. **Genuine agent error / instability** (row 12; the 58/12 branches of
   row 11): wrong pipeline or unstable intermediate step, though row 11's
   branches were invited by the question's wording.
7. **Self-inflicted environment failure** (the nine non-responses): the
   harness's own `R_SPECIFIC_GUIDELINES` install idiom meets an image without
   `BiocManager`. See `env/SETUP.md`.
8. **Budget exhaustion** (row 13).
9. **Key not reproducible from the shipped capsule** (rows 16–18): either
   provenance unidentified (bix-43) or underdetermined by the data (bix-4).

Categories 1–5, 7 and 9 are properties of the benchmark; 6 and 8 are
properties of the agent. That balance — on this sample, most scored failures
are the benchmark's — is the uncomfortable and interesting result, and it is
now measured rather than argued.

## Reproducibility caveat for the writeup

The bix-8 and bix-49 verifications are fully deterministic (spreadsheet counts
and DESeq2 on fixed inputs). The bix-26 and bix-1 verifications are not:
`enrichKEGG` queries the **live KEGG REST service**, which is updated
continuously and offers no public versioned snapshot, and GO enrichment
depends on the **org.Hs.eg.db release** (the image pins a ~2024 build; the
author's version is unknown). Pathway memberships and term gene sets move, so
the exact matches (q3 = 11, q4 = 5, q5 = 1-vs-3) are claims *as of
2026-08-23* and could drift under a future KEGG. State the recomputation date
wherever these numbers appear. This is also itself a finding: any answer key
built on "the latest KEGG db" (bix-26-q4's own words) has a shelf life the
benchmark never declares.

## What I did not review, and why

The other **nine non-responses** are one documented mechanism: the agent
follows the harness's own `R_SPECIFIC_GUIDELINES` install idiom, the image
lacks `BiocManager`, and the run dies at 6–17 of 40 actions. Reading more of
them adds nothing. See `env/SETUP.md`.

Questions at 90–100% graded-correct — `bix-8-q1/q2/q3`, `bix-26-q3`,
`bix-49-q5` — were originally skipped as uninformative; the >1% scan pulled
`bix-49-q5` and single replicates of `bix-8-q2/q3` back in (rows 4, 5, 10).

## What remains for manual review

The computational questions are settled; what is left is domain judgment and
provenance work no script can do:

- **Decide the framing of the sex covariate.** Adjusting for sex on this
  design is arguably the *better* analysis — the defect is that it is
  unstated, not that it is wrong. The writeup should say both, without
  letting "the key is defensible" soften "the key is unanswerable from the
  question text."
- **Check the capsule authors' own notebooks for provenance.** The Hugging
  Face capsules ship the authors' analysis notebooks; the harness strips them
  from the agent's data folder. Reading them could (a) confirm the
  `~ sex + condition` design directly, (b) settle bix-43's 677, and
  (c) show whether bix-26-q5's key really used raw p. This converts three
  "reproduces under scenario X" claims into documented fact. (This also
  covers the Phase 1 leftover: read two expert notebooks in full.)
- **Pull quotes for the writeup.** The verified rows need one or two
  verbatim notebook excerpts each — the agent printing 680 before
  deduplicating, the "Wait — pathways don't have fold changes" cell in the
  bix-26 GSEA replicate — to make the taxonomy concrete.
- **Decide what to do with the pilot rows** (16–18). Single truncated runs on
  dropped capsules: report as an appendix observation, or exclude and note
  the exclusion. Recommendation: appendix, clearly labeled K=1.
- **Sanity-check my two remaining judgment calls:** treating bix-8-q2's 2×2
  as defensible rather than wrong, and classifying the 58-answer replicates
  as agent error *invited by* the question rather than pure agent error. Both
  affect the benchmark-vs-agent tally by one row.
