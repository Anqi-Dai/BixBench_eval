# Start here — session handoff

**State as of 2026-08-23: all data collection and all failure verification are
done. What remains is the R analysis and the writeup. Neither costs money.**

Total spend to date: **$80.18** (`results/spend_log.csv`, every billed call).

---

## Where things live

| | |
|---|---|
| This repo | `/Users/daia1/Evals/BixBench` |
| Upstream harness clone | `/Users/daia1/Evals/BixBench-upstream` (not a submodule; cloned separately) |
| Python env | `../BixBench-upstream/.venv`, **CPython 3.13.15** — 3.12 cannot run the agentic path |
| API keys | `../BixBench-upstream/.env` (gitignored both sides) |
| Agent trajectories | `../BixBench-upstream/data/trajectories/pricing_bix8/pricing_bix8_claude45/` — 159 JSON + 159 JSONL, ~216 MB, **not in git** |
| Capsule data | `../BixBench-upstream/data/capsules/` (pulled from Hugging Face) |

**Run anything in this repo as:**

```bash
uv run --project /Users/daia1/Evals/BixBench-upstream --python 3.13 python py/<script>.py
```

The `py/verify_*.py` and `R/verify_*.R` scripts each carry their own `docker run`
line in the header and need Docker Desktop running.

---

## What the dataset is

**140 agent trajectories** — 3 capsules × K=10 replicates, claude-sonnet-4-5
(pinned `20250929`), temperature 1.0, `max_steps: 40`. Plus 19 K=1 pilot
trajectories across 4 other capsules.

| Capsule | Questions | Replicates | Answered |
|---|---:|---:|---:|
| `bix-8` | 6 | 10 | 60/60 |
| `bix-49` | 5 | 10 | 48/50 |
| `bix-26` | 3 | 10 | 22/30 |

All three come from different source papers, so they are statistically
independent. Every ground truth is numeric — which is why replicate agreement can
be computed with no grader in the loop.

## Results files

| File | Grain | Holds |
|---|---|---|
| `results/agent_runs.csv` | trajectory | answer, ideal, actions, truncation and non-response flags |
| `results/consistency.csv` | question | replicate agreement at 0%, 1%, 5% tolerance |
| `results/grader_noise_agent.csv` | grade | 130 answers × {gpt-4o, claude} × 10 replicates |
| `results/grader_noise_gpt5.csv` | grade | same 130 answers × gpt-5 × 10 replicates |
| `results/refusal_audit.csv` | grade | 408 zero-shot regrades recovering the discarded `refused` verdict |
| `results/capsule_pilot_log.csv` | capsule | all 54 capsules: metadata + measured cost/runtime where piloted |
| `results/spend_log.csv` | run | every billed call |

## The findings, already established — do not re-derive

1. **Replicate agreement: 69.9% exact, 85.2% within 1%, 88.2% within 5%** over 549
   pairs. Computed grader-free. Instability differs in *kind* by capsule:
   `bix-49`'s disagreements vanish at 5% tolerance, `bix-8`'s do not.
2. **BixBench's default grader contradicts itself on 14.6% of identical answers**
   (gpt-4o, 19/130). gpt-5 does so on 0.8%, claude-sonnet-4-5 on 1.5%. The two
   current models agree with each other on **0/130** — so it is generation, not
   family, and the remedy is a one-line config change.
3. **71.4% of what the benchmark scores as an incorrect answer is the model
   declining to answer** (zero-shot substrate, 284/398).
4. **10 of 140 trajectories submitted nothing.** Nine died following the harness's
   own `R_SPECIFIC_GUIDELINES` install idiom in an image lacking `BiocManager`;
   one exhausted its step budget.
5. **Most scored failures trace to the benchmark, not the model.** Every deviation
   was recomputed from raw capsule data inside the benchmark's own image. See
   `env/REVIEW_REPORT.md` — the authoritative document for Phase 4.

## Documents, in reading order

1. `README.md` — finding-first, with the capsule-selection diagram
2. `bixbench_project_brief.md` — goals and scope, with checkboxes (35 done, 11 open)
3. `env/REVIEW_REPORT.md` — **the failure taxonomy, verified by recomputation**
4. `env/SETUP.md` — environment, friction log, harness defects
5. `env/DESIGN.md` — grader design and the analysis plan for this dataset
6. `env/PAPER_NOTES.md` — what the paper actually says, verified
7. `env/CAPSULE_SELECTION.md` — why these three capsules

---

## What is left

**Phase 3 — R analysis (next).** Nothing else blocks it.

The outcome has three states, not two, and collapsing them would reproduce the
defect this project documents. Fit two stages:

```r
# stage 1 — did the agent produce an answer at all?
brm(responded ~ 1 + (1 | capsule/question), family = bernoulli())

# stage 2 — given an answer, was it graded correct?
brm(correct ~ 1 + (1 | capsule/question), family = bernoulli(),
    data = subset(d, responded))
```

Caveats to carry into the writeup:

- **Three capsules cannot identify a capsule-level variance.** Use a
  weakly-informative prior on the SD and report the intercepts as partially
  pooled, not as a measured between-capsule variance. Question level (14 groups ×
  10 observations) is well supported.
- `bix-49-q4`, `q5` and `bix-26` questions have 9 or fewer usable replicates.
  Unbalanced K is fine; do not silently drop.
- **Which grader defines `correct` matters.** gpt-4o and the two current models
  disagree on 19/130. Report the model under a current grader and note the
  sensitivity, rather than treating any one as truth.

**Phase 4 — writing up the taxonomy.** The analysis is done; only prose remains.
Still open: read two expert notebooks in full, and compare the 10 notebooks for a
single question to see whether the agent fails the same way each time.

**Phase 5 — the writeup.** 1,200–1,800 words, finding first. Then Zenodo DOI, then
make the repo public.

## Two cautions for the writeup

- The "benchmark is wrong more often than the model" result rests on questions
  from a small number of capsules, and the entity-conflation cases all come from
  `bix-8`. State the base clearly rather than generalizing to all 53 capsules.
- Do not write that BixBench reports a single-run point estimate. **The authors
  replicate ten times** and pool. The defensible claim is that they generate the
  dispersion and discard it.
