# Phase 0 — Environment setup and friction log

Setup friction is a finding, not an inconvenience: how hard a benchmark is to run
end to end is part of how usable it is. Everything that broke, and what fixed it,
gets recorded here as it happens.

## Host

| | |
|---|---|
| Machine | macOS (Darwin 25.5.0), Apple Silicon |
| Started | 2026-08-19 |
| Upstream harness | `Future-House/BixBench` @ `4931118` (2025-10-06) |
| Clone location | `../BixBench-upstream` (sibling, deliberately outside this repo) |

## Answers to the Phase 0 open questions

### Q1. Does the harness expose a temperature setting?

Yes, and this is more interesting than expected.

Temperature lives at `agent.agent_kwargs.llm_model.temperature` in the run
configuration YAML (`bixbench/run_configuration/*.yaml`). **Every shipped config
sets it to `1.0`** — `generate_trajectories.yaml`, `claude_image.yaml`,
`4o_image.yaml`, and the rest.

The published BixBench numbers were therefore produced by sampling at temperature
1.0, not greedily. That strengthens the premise of this study rather than
weakening it: the reliability question is not a contrived stress test at an
unusual setting, it is a question about the configuration the benchmark actually
shipped and reported.

### Q2. Does the harness support replicates natively?

Yes. `bixbench/generate_trajectories.py` takes `--replica_id`, and
`scripts/run_agentic.sh` loops `for replica_id in $(seq 0 5)` over four model
configs (`NUM_REPLICAS=5`, so six replicas: 0–5).

Important detail: `replica_id` is *purely a namespacing device*. Tracing it
through the code, it appears in exactly two places — the trajectory output
filename (`{problem_id}_replica_{n}.json`) and the per-question working directory.
**No random seed is set anywhere.** All variation between replicas comes from LLM
sampling at temperature 1.0.

Two consequences:

- Replicas are genuine independent draws, which is exactly what Q1 needs. No
  custom replicate loop has to be written.
- Runs are not bit-for-bit reproducible, and cannot be made so. The writeup must
  say this plainly.

### Q3. What is persisted per run, and are notebooks retrievable?

Yes, notebooks are retrievable — this is the single most important answer for the
failure-taxonomy phase.

`generate_trajectories.py` writes, per question per replica:

- `{problem_id}_replica_{n}.json` containing `agent_answer`, `ideal_answer`,
  `problem`, `notebook_stats`, `num_actions`, `model`, `run_name`, the MCQ
  options, and **`nb` — the full notebook object**, embedded inline.
- `{problem_id}_replica_{n}.jsonl` — the complete agent trajectory.

So Phase 4 needs no extra instrumentation. Everything required to read what the
agent actually did is already on disk after a run.

### Q4. Per-capsule API cost

**Not yet measured.** Requires a live run; deferred until Docker and Hugging Face
auth are working. To be measured on a handful of real calls rather than estimated,
per the project's own guardrail.

### Q5. Can capsules be filtered by subject from metadata?

Partly, and for free. See `py/scan_capsule_subjects.py`.

The repo ships zero-shot baseline CSVs
(`bixbench-v1.5_results/zero_shot_baselines/*.csv`) with one row per question:
`uuid, question, predicted, target, unsure, evaluation_mode, grade, correct, sure`.
That allows a subject scan by keyword over question text with no gated download
and no API spend: 205 open-answer questions across 54 capsules.

Capsules per topic, by keyword match on question text:

| Topic | Capsules |
|---|---|
| RNA-seq / differential expression | 13 |
| variant / genomics | 10 |
| enrichment / pathway | 9 |
| clinical / survival | 2 |
| **microbiome / metagenomics** | **0** |
| single-cell | 0 |
| imaging | 0 |

**Flag: the zero microbiome hit needs confirming against the real capsule
metadata before any planning depends on it.** This scan reads *question text
only*, and question text can name a result without naming the assay. But if it
holds up, the strongest single domain available here is not represented in
BixBench, and the failure taxonomy should be built on the RNA-seq /
differential-expression cluster instead — which is well covered, and is squarely
within scope.

### Q6. Is the LLM grader deterministic?

**No, not by default — and this is the confound the brief flagged.**

`grade_outputs.py` builds the open-answer grader as `gpt-4o` with
`temperature` defaulting to **1.0**. So out of the box, some observed
inconsistency between replicas is grader noise, not agent noise.

Two things make this tractable:

1. **Temperature is a CLI flag** (`--temperature`), so the grader can be pinned
   near 0. That reduces grader noise but does not eliminate it; LLM inference is
   not guaranteed deterministic even at temperature 0.
2. **Most questions are not LLM-graded at all.** `evaluation_mode` is set per
   question, and across the 205 open-answer questions the split is:

   | verifier | n | share |
   |---|---|---|
   | `llm_verifier` | 83 | 40.5% |
   | `str_verifier` | 61 | 29.8% |
   | `range_verifier` | 61 | 29.8% |

   `str_verifier` and `range_verifier` are deterministic comparisons. Roughly
   **60% of the benchmark is immune to grader noise by construction.**

Planned control, cheap enough to run before any agent run: take the *already
shipped* baseline answers and re-grade the identical answers K times. Same inputs,
K grades. Any disagreement is pure grader noise, measured with zero agent cost.
That gives a grader-noise floor to subtract from — or at minimum to report
alongside — the agent self-consistency rate.

## Friction encountered

- **Docker daemon not running.** Docker 29.4.2 is installed but the daemon is
  down. Docker Desktop has to be started before the notebook environment
  (`futurehouse/bixbench:aviary-notebook-env`) can be pulled.
- **No Hugging Face auth.** `huggingface-cli` is installed (miniforge) but no
  cached token exists. The dataset is gated, so `huggingface-cli login` must be
  run interactively.
- **Python version mismatch risk.** System Python is 3.14.6. `pyproject.toml`
  requires `>=3.12`, which 3.14 nominally satisfies, but the dependency set
  includes `fhaviary`, `fhda` (a git dependency pinned to `v1.5.0`), `ldp`, and
  `fhlmi` — none of which are likely to have been tested on 3.14. Plan is a
  dedicated **3.12** virtualenv rather than fighting wheel availability.
- **`uv` not installed.** Upstream ships a `uv.lock`, so `uv` is the intended
  installer and reproduces the exact tested dependency set. Worth installing
  rather than resolving with pip.
- **Inconsistent capsule id capitalization upstream.** Two question uuids are
  `Bix-33-q6` and `Bix-47-q3`; every other uuid is lowercase `bix-`. A
  case-sensitive join on capsule id silently drops those rows. Handled in
  `py/scan_capsule_subjects.py`; noting it because it is exactly the class of
  silent-data-loss bug this project is about.
- **Question count differs from the paper.** The paper reports 296 questions; the
  shipped v1.5 open-answer baseline has 205 rows across 54 capsules (the paper
  says 53). Not yet reconciled — possibly an MCQ/open split or a v1 vs v1.5
  difference. Resolve before citing any headline figure.

## Next steps

1. Start Docker Desktop; pull `futurehouse/bixbench:aviary-notebook-env`.
2. `huggingface-cli login` (interactive — needs a token with access to the gated
   `futurehouse/BixBench` dataset).
3. Install `uv`; create a Python 3.12 environment from `uv.lock`.
4. Run the grader-noise control (Q6) — no agent runs, minimal cost.
5. Confirm the microbiome-absence finding (Q5) against real capsule metadata.
6. Only then run `run_zeroshot.sh` end to end on a small subset.
