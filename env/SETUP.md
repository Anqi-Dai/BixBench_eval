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

**No — and it is worse than a first reading of the code suggests.**

`grade_outputs.py` builds the open-answer grader as `gpt-4o` with `temperature`
defaulting to **1.0**. Temperature is a CLI flag (`--temperature`) so it can be
pinned near 0, which reduces grader noise without eliminating it; LLM inference
is not guaranteed deterministic even at temperature 0.

#### `evaluation_mode` is an entry point, not a grading method

An earlier version of this document claimed roughly 60% of the benchmark was
"immune to grader noise by construction", reading the per-question
`evaluation_mode` field as the grading method. **That was wrong.** Tracing
`OpenEndedGrader.grade` in `bixbench/graders.py` shows what each mode does in the
open-answer path:

| `evaluation_mode` | n | What actually happens |
|---|---:|---|
| `llm_verifier` | 83 | Always calls the LLM |
| `range_verifier` | 61 | Routes to `_grade_range_llm_verifier` — **also always calls the LLM** |
| `str_verifier` | 61 | Exact match, then substring match; **falls through to `_grade_llm_verifier` if both fail** |

Two traps here. First, the deterministic `_grade_range_verifier` exists but is
unreachable from the open-answer path — it is dead code there, reachable only via
`MCQGrader`. The name suggests a numeric range comparison; the open-answer path
asks an LLM instead. Second, `str_verifier`'s fallthrough is live because
`grade_outputs.py` passes `partial_match=True, llm_match=True`.

Replaying that logic against the shipped baselines gives the real exposure:

| Baseline | Deterministic | LLM-graded |
|---|---:|---:|
| gpt-4o answers | 2 / 205 | **203 / 205 (99.0%)** |
| claude-3-5-sonnet answers | 0 / 205 | **205 / 205 (100%)** |

**Effectively every open-answer grade is an LLM judgment.** There is no
grader-noise-free subset to fall back on.

#### Consequences

- The grader-noise control is no longer a nicety; it is **load-bearing**. Nothing
  else bounds how much observed inconsistency is the grader rather than the agent.
- Capsules cannot be selected to be grader-noise-free. Exposure also is not fixed
  in advance: whether a `str_verifier` question short-circuits depends on the
  agent's own answer that replicate, so a capsule's exposure varies run to run.
- This is itself a finding. A benchmark that presents three verifier modes, two of
  them named as if deterministic, while routing ~100% of open answers through an
  LLM judge, is reporting scores with more judgment-noise baked in than the
  configuration surface suggests.

#### The control

Take the *already shipped* baseline answers and re-grade the identical answers K
times. Same inputs, K grades — any disagreement is pure grader noise, at zero
agent cost. That gives a noise floor to report alongside the agent
self-consistency rate.

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

## Environment build (resolved)

| | |
|---|---|
| Installer | `uv` 0.12.5 (via Homebrew — avoids piping a remote install script to a shell) |
| Interpreter | CPython **3.12.14**, installed by `uv python install 3.12` |
| Venv | `../BixBench-upstream/.venv`, built with `uv sync --python 3.12` from the shipped `uv.lock` |

Using `uv sync` against the committed lockfile rather than resolving with pip
means the dependency set is the exact one upstream tested, including the git
dependency `fhda @ git+https://github.com/Future-House/data-analysis-crow@v1.5.0`.

Import check passed for the packages most likely to break on a newer
interpreter, plus the harness itself: `pandas` 2.2.3, `numpy` 2.2.3, `aviary`,
`fhda`, `ldp`, `lmi`, `bixbench`. The 3.14 concern was real but is now moot —
nothing was fought, the 3.12 environment simply resolved.

Repeat with:

```bash
cd ../BixBench-upstream && uv sync --python 3.12
```

### Hugging Face CLI rename

`huggingface-cli` is now a **deprecated no-op**. Running `huggingface-cli login`
prints a deprecation warning and exits without storing a token, so it looks like
it worked and does not. The working command is `hf auth login`, checked with
`hf auth whoami`. Token lands in `~/.cache/huggingface/`.

Worth recording because the BixBench README still instructs `huggingface-cli
login` — a silent no-op in a documented setup step is exactly the kind of
friction this log exists for.

## The execution image: what the agent can actually reach

`futurehouse/bixbench:aviary-notebook-env` pulled cleanly, **18.3 GB**, but it
was built **19 months ago** (~Jan 2025). Interpreters are correspondingly dated:
Python 3.12.2, **R 4.3.3 (2024-02-29)**. 254 Python packages, 333 R packages.

Contents matter more than versions here, because the agent can only analyze with
what is installed. Checked directly with `find.package()` and
`importlib.metadata`, not by import success:

| Capability | R | Python |
|---|---|---|
| Differential expression | `DESeq2` 1.42.0 — **`edgeR` and `limma` absent** | `pydeseq2` 0.4.12 |
| Enrichment / pathway | `clusterProfiler` 4.10.0 | `gseapy` 1.1.4 |
| Single-cell | **`Seurat` absent** | `scanpy` 1.10.4, `anndata` 0.11.1 |
| Microbiome / ecology | **`phyloseq` absent, `vegan` absent** | **`skbio`, `biom-format`, `qiime2` all absent** |
| General | `tidyverse` 2.0.0 | `pandas` 2.2.3, `numpy` 2.0.2, `scipy` 1.14.1, `statsmodels` 0.14.4 |

Three consequences for this study:

**The microbiome finding is corroborated independently.** Q5's keyword scan found
zero microbiome capsules from question text alone. The execution image contains
no microbiome tooling whatsoever — not `phyloseq`, not `vegan`, not `skbio`, not
`biom-format`. Two independent lines of evidence now point the same way, so the
failure taxonomy should be built on the RNA-seq / differential-expression
cluster. Still worth a final confirmation against capsule metadata, but this is
no longer a single fragile keyword result.

**Differential expression is effectively DESeq2-only in R.** With 13 capsules
touching RNA-seq, and `edgeR` and `limma` both missing, the agent's R method
choice is far more constrained than a working bioinformatician's would be. That
creates a failure mode the brief's candidate taxonomy does not yet name:
*reached for a method the environment does not have*. Whether the agent then
adapts sensibly, silently substitutes something inappropriate, or gives up is
exactly the kind of distinction manual notebook review can draw.

**Single-cell work is Python-only.** `scanpy` is present and `Seurat` is not, so
any single-cell capsule forces a language choice regardless of what the expert
notebook did.

### Open question raised by this

Does the container have network access during a run, letting the agent
`install.packages()` or `pip install` its way around a gap? If yes, "package
absent" becomes a *time and token* cost rather than a hard wall, and possibly a
distinctive failure mode of its own. Not yet determined — resolve during the
first real run.

## Hugging Face access — and a correction

`hf auth login` succeeded (user `anqidai`). Two corrections to the brief follow
from actually querying the hub:

**The dataset is not gated.** `dataset_info('futurehouse/BixBench').gated` is
`False`. The brief and the upstream README both say authentication is required;
it is not. A token is still worth having for rate limits, but the login is not a
blocker for anyone reproducing this.

**The dataset has 64 capsule zips, not 53.** The paper reports 53 capsules and
296 questions. The hub repo holds 64 `CapsuleFolder-*.zip` files, while
`BixBench.jsonl` (v1.5) describes **205 questions across 54 capsules**. Three
different counts. The metadata `version` field says `1.5`, so the paper's figures
are presumably v1. Nothing here should cite a headline number without saying
which version it came from.

## Q5, settled: capsules can be filtered from metadata, and there is no microbiome

`BixBench.jsonl` carries a curator-assigned `categories` field per question, so
subject matter is read directly rather than inferred. Full category list across
all 54 capsules:

| n | Category | | n | Category |
|---:|---|---|---:|---|
| 23 | Genomics | | 2 | Network Biology |
| 19 | Transcriptomics | | 2 | Functional Genomics |
| 18 | RNA-seq | | 2 | Machine Learning and AI |
| 18 | Differential Expression Analysis | | 2 | Epigenomics |
| 14 | Phylogenetics and Evolutionary Analysis | | 1 | Single-Cell Analysis |
| 12 | Whole Genome Sequencing (WGS) | | 1 | Proteomics |
| 8 | Sequence Analysis | | 1 | Integrative Omics |
| 7 | Genomic Variant Analysis | | 1 | Phylogenetics |
| 5 | Other | | 1 | SNP Analysis |
| 4 | Imaging | | 1 | Antimicrobial Resistance |

**There is no microbiome or metagenomics category.** The nearest match is a
single "Antimicrobial Resistance" capsule, which is bacterial genomics rather
than community profiling.

That conclusion now rests on three independent lines of evidence:

1. Keyword scan over question text — zero hits.
2. Execution image carries no microbiome tooling — no `phyloseq`, `vegan`,
   `skbio`, `biom-format` or `qiime2`.
3. Curator-assigned metadata categories — no such category exists.

**Decision: the failure taxonomy targets the RNA-seq / differential-expression
cluster** — 22 capsules, 81 questions, the largest coherent domain in the
benchmark and squarely within scope.

### Another silent-corruption wart

`categories` is stored two different ways: most records use a plain
comma-separated string, but 57 of 205 hold the *repr of a Python list*
(`"['Genomics', 'Phylogenetics']"`). Splitting on commas alone shreds the second
form into fragments like `"['Genomics'"` and yields a category table that looks
plausible and is wrong. Handled in `py/scan_capsules.py`; logged because it is
the second such wart found (after the `bix-`/`Bix-` capitalization) and both are
the kind of defect this project exists to notice.

## Capsule selection for the first replicate run

An earlier draft picked capsules to span the "grader-exposure spectrum", on the
belief that `str_verifier` capsules were graded deterministically. Q6 above
shows they are not, so **that rationale is void** — there is no grader-noise-free
capsule to anchor on, and `bix-13` is not the clean control it was described as.

Selection therefore falls back to ordinary criteria: stay inside the RNA-seq /
differential-expression cluster, and prefer capsules with enough questions to
estimate a per-capsule consistency rate.

Proposed starting three (16 questions), per the brief's three-capsule guardrail:

| Capsule | Questions | Categories |
|---|---:|---|
| `bix-8` | 6 | Differential Expression Analysis, Epigenomics, RNA-seq |
| `bix-43` | 5 | Differential Expression Analysis, RNA-seq, Transcriptomics |
| `bix-53` | 5 | Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics |

These are the three largest capsules in the cluster, which matters because the
per-capsule varying intercept in the `brms` model is estimated from within-capsule
questions. Separating agent noise from grader noise now rests entirely on the
regrade control, not on capsule choice.

## Q4, partial: measured grader cost

Measured rather than estimated, per the project's own guardrail. The shipped
baseline CSV holds the exact question/target/predicted triples the grader sees,
so the real prompts were tokenized with `tiktoken` against gpt-4o's encoding.

An earlier figure here counted only the 83 `llm_verifier` questions and put K=20
at ~$0.81. Q6 above corrects that: **203 of 205 questions reach the LLM**, so the
call volume is 2.4x higher. Corrected numbers, using each mode's actual prompt
template:

- **203 LLM calls per replicate** (99.0% of questions)
- **177 input tokens per call** (median 169)
- ~10 output tokens — the response is just `<grade> correct </grade>`

| Replicates | Calls per grader | gpt-4o | Claude Sonnet 4.5 | Both |
|---:|---:|---:|---:|---:|
| 10 | 2,030 | ~$1.10 | ~$1.38 | ~$2.48 |
| **20** | **4,060** | ~$2.20 | ~$2.77 | **~$4.97** |

Still cheap enough that replicate count is not the binding constraint, and the
dual-grader decision still costs only a few dollars. K=20 remains the
recommendation. Agent-run cost — the expensive half of Q4 — still has to be
measured on real trajectories.

**Blocked on credentials.** Neither `OPENAI_API_KEY` nor `ANTHROPIC_API_KEY` is
present in the environment or in any `.env`. They belong in
`../BixBench-upstream/.env`, since `generate_zeroshot_evals.py` resolves
`Path(".env")` relative to the working directory.

## Next steps

1. Add API keys to `.env` (blocking).
2. Run the grader-noise control (Q6) at K=20, ~$0.81.
3. Run `run_zeroshot.sh` end to end on `bix-13`, `bix-43`, `bix-24`.
4. Measure real agent-run cost (rest of Q4) on those trajectories.
