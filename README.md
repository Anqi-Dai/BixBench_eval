# What the score hides: an audit of BixBench

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22151932.svg)](https://doi.org/10.5281/zenodo.22151932)

BixBench is FutureHouse's benchmark for bioinformatics agents. It does
something right that most benchmarks skip — it runs every analysis ten times —
but those runs are pooled into a single accuracy number, and everything the
pooling flattens goes unexamined. This study audits what that score hides, on
three capsules (14 questions, 140 agent runs, ~$80): the run-to-run variation,
the grader's reliability, and the answer keys themselves. The headline:
**most of what the benchmark scores as agent failure does not come from the
agent.** 73 of 80 incorrect answers trace to the answer key or the question's
wording — verified by re-deriving both the key and the agent's answer from the
raw data — and 9 of the 10 runs that never answered died following the
harness's own package-install instruction. The agent's own share is 8 runs out
of 140.

**The full writeup is [writeup.md](writeup.md).** Four findings, one per
figure:

1. **[Grader disagreement follows model generation, not model family](writeup.md#the-grader-is-part-of-the-instrument)**
   — two current-generation graders from different families agree on all 130
   answers; the shipped previous-generation grader contradicts itself on 14.6%
   of them.
2. **[No answer is its own outcome, not a wrong answer](writeup.md#no-answer-is-its-own-outcome-not-a-wrong-answer)**
   — 10 runs never answered; 9 died in the harness's own install instruction,
   1 ran out of steps.
3. **[Correctness is a property of the question, not luck](writeup.md#correctness-is-a-property-of-the-question)**
   — per-question success rates are bimodal: near-certain success or
   near-certain failure, almost nothing between.
4. **[Most incorrect answers trace to the benchmark](writeup.md#where-the-failures-actually-come-from)**
   — hidden analysis choices in the key, genes-versus-transcripts conflation,
   and keys that contradict their own questions' thresholds.

<img src="results/figures/fig4_failure_causes.png" alt="Most incorrect answers trace to the benchmark" width="540">

## Where to read

| Document | What it holds |
|---|---|
| [writeup.md](writeup.md) | The study, finding-first (~1,700 words, 4 figures) |
| [Interactive run audit](results/figures/fig4_interactive.html) | All 140 runs; hover any run for its verified cause |
| [env/REVIEW_REPORT.md](env/REVIEW_REPORT.md) | Case-by-case failure attribution, verified by recomputation |
| [env/SETUP.md](env/SETUP.md) · [env/DESIGN.md](env/DESIGN.md) · [env/PAPER_NOTES.md](env/PAPER_NOTES.md) · [env/CAPSULE_SELECTION.md](env/CAPSULE_SELECTION.md) | Environment and friction log · grader design · what the paper says, verified · capsule choice |
| [Agent trajectories on Zenodo](https://doi.org/10.5281/zenodo.22151974) | All 159 runs with full notebooks (~216 MB), deposited as a dataset |

## Choosing the capsules

Three capsules out of 54. The diagram's argument
is **which filters were free and which had to be paid for**.

```mermaid
flowchart TD
    START["<b>54 capsules</b><br/>BixBench v1.5 · 205 questions"]:::pool

    START --> SURVEY{{"<b>SURVEY</b><br/>metadata + image inspection<br/><i>$0</i>"}}:::survey

    SURVEY -->|"curator categories:<br/>no microbiome capsule exists"| CLUSTER["<b>RNA-seq / DE cluster</b><br/>22 capsules · 81 questions"]:::pool
    SURVEY -->|"questions need BWA, GATK,<br/>Trimmomatic — absent from image"| R61["bix-61<br/><i>unrunnable</i>"]:::rej

    CLUSTER --> PILOT{{"<b>PILOT at K=1</b><br/>one replica each<br/><i>$0.84 – $7.62</i>"}}:::pilot

    PILOT -->|"all 5 questions stopped at<br/>max_steps=20 · 2 gave no answer"| R43["bix-43, bix-53<br/><i>truncated</i>"]:::rej
    PILOT -->|"$7.62/replica — 5.6× bix-8<br/>despite the shortest questions"| R4["bix-4<br/><i>too expensive</i>"]:::rej
    PILOT -->|"$1.35 · 9–14 actions<br/>never near the ceiling"| S8["<b>bix-8</b><br/>6 questions"]:::sel
    PILOT -->|"$2.36 · independent family"| S26["<b>bix-26</b><br/>3 questions"]:::sel
    PILOT -->|"$0.84 — cheapest,<br/>but only 2 questions"| B1["bix-1"]:::mid

    B1 --> FAM["<b>within-family test</b><br/>bix-1 vs bix-49 differ by <b>3%</b><br/>bix-1 vs bix-26, same topic, by <b>87%</b>"]:::find
    FAM -->|"family predicts cost;<br/>topic and question length do not"| S49["<b>bix-49</b><br/>5 questions"]:::sel
    FAM -.->|"superseded — same family,<br/>fewer questions"| DROP1["bix-1<br/><i>dropped</i>"]:::rej

    S8 -.->|"shares a source paper with bix-8;<br/>3 capsules cannot identify<br/>a paper-level variance"| R37["bix-37<br/><i>not independent</i>"]:::rej

    S8 --> FINAL["<b>K=10 campaign</b><br/>14 questions · 140 trajectories"]:::final
    S49 --> FINAL
    S26 --> FINAL

    classDef pool fill:#e8eef7,stroke:#4a6fa5,stroke-width:2px,color:#1a2b45
    classDef survey fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#12305e
    classDef pilot fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#5c3a00
    classDef sel fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#0f3d20
    classDef rej fill:#fee2e2,stroke:#dc2626,stroke-width:1.5px,color:#5c1010
    classDef mid fill:#f3f4f6,stroke:#6b7280,stroke-width:1.5px,color:#1f2937
    classDef find fill:#ede9fe,stroke:#7c3aed,stroke-width:2px,color:#3b1f7a
    classDef final fill:#16a34a,stroke:#14532d,stroke-width:3px,color:#ffffff
```

Two eliminations cost nothing — the curators' own `categories` field shows no
microbiome capsule exists, and listing the Docker image shows `bix-61` needs BWA,
GATK and Trimmomatic that are not installed. Everything below the amber box
required spending money, and **none of it was predictable**: `bix-4` had the
shortest questions of any candidate, was forecast cheapest, and cost 5.6× `bix-8`.

One rule survived. Capsules from the same source paper cost within **3%** of each
other per rollout; capsules sharing a *topic* but not a paper differ by **87%**.
So one pilot generalizes across a family, and neither topic nor question length
predicts anything. Full reasoning in
[`env/CAPSULE_SELECTION.md`](env/CAPSULE_SELECTION.md).

## Scope, stated up front

Small N: 3 capsules of 54, 14 questions, one agent configuration, one pinned model
at temperature 1.0. This is a structured probe, not a replication of the BixBench
leaderboard. It cannot speak to self-preference (one answering model),
cross-model comparison, temperature dependence, or the benchmark as a whole.

## Layout

| Path | What lives here |
|---|---|
| [writeup.md](writeup.md) | The study writeup |
| `env/` | Setup and friction log, design notes, capsule selection, paper notes, the review report |
| `py/` | Capsule survey, replicate-run pipeline, grading, verification scripts |
| `R/` | Two-stage `brms` model, figures, key-verification scripts |
| `results/` | Tidy CSVs, the spend ledger, model summary, and the four figures |
| [references.bib](references.bib) | Verified references for the writeup |
| `scripts/` | Campaign runner and run watcher |
| `notebooks/` | Curated agent notebooks quoted in the failure taxonomy |
| `data/` | Capsule data (gitignored; pulled from Hugging Face) |

## Upstream

- Paper: [arXiv:2503.00096](https://arxiv.org/abs/2503.00096) — *BixBench: a Comprehensive Benchmark for LLM-based Agents in Computational Biology* (17% open-answer accuracy; no better than random on MCQ)
- Harness: [Future-House/BixBench](https://github.com/Future-House/BixBench)
- Agent: [Future-House/data-analysis-crow](https://github.com/Future-House/data-analysis-crow)
- Dataset: [futurehouse/BixBench](https://huggingface.co/datasets/futurehouse/BixBench) — public, despite the README's login step

## License

MIT — see [LICENSE](LICENSE).
