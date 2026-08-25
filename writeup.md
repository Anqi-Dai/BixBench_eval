# What BixBench's discarded variance says — a reliability study

*Draft. Target 1,200–1,800 words. Sections follow the plan in HANDOFF.md;
references live in `references.bib`, every entry verified against arXiv.*

## The finding

*(to write — the three-sentence lead: the dispersion was generated and never
reported; most scored failure traces to the benchmark; the fixes are small.
State the base immediately: 3 capsules, 14 questions, 140 trajectories, one
model, $80.)*

## Why this benchmark, why this question

Agents are already doing bioinformatics. You can hand one a count matrix and a
question and get a full differential-expression analysis back in minutes — this
is happening now, and it is speeding the field up in a way nothing before it
did. Whether we can trust that work comes down to evaluation. And benchmarks
for biology agents are young: a small number exist, all from the last two years
— [LAB-Bench](https://arxiv.org/abs/2407.10362) and its February 2026 successor
[LABBench2](https://arxiv.org/abs/2604.09554) for research tasks,
[ScienceAgentBench](https://arxiv.org/abs/2410.05080) for data-driven analysis
across four disciplines — and the methods for checking the benchmarks
themselves — is the grader consistent, is the answer key right, is one accuracy
number enough — are younger still.

[BixBench](https://arxiv.org/abs/2503.00096), FutureHouse's benchmark for
bioinformatics agents, does something right that most benchmarks skip: it runs
every analysis ten times, because agents don't give the same answer twice. But
those ten runs get folded into a single accuracy fraction, and the spread — how
often the agent disagrees with itself — is never reported. I've spent seven
years doing statistics on messy clinical data, where the spread usually *is*
the story. So that's the question I went after: what does the discarded
variance say?

## What I ran

*(to write — 3 capsules × 10 replicates, numeric ground truths, grading as a
separately replicated step with three graders; the one design table.)*

## The grader is part of the instrument

*(to write — fig 1: gpt-4o self-contradicts on 14.6% of identical answers and
flips two whole questions; the two current-generation models agree 130/130
across families. Generation, not vendor; the remedy is one config line.)*

## An agent run has three outcomes, not two

*(to write — fig 2: the no-answer runs, the harness's own install idiom, and
why collapsing no-answer into incorrect misattributes harness defects to the
model.)*

## Where the failures actually come from

*(to write — fig 3: incorrect and no-answer runs split by verified cause,
warm = benchmark-attributable, cool = agent-attributable; one concrete example,
link REVIEW_REPORT.md.)*

## Correctness is a property of the question

*(to write — fig 4: the two-stage model, bimodal per-question rates, what
partial pooling buys; bridge to the taxonomy.)*

## Limitations and what I'd do next

*(to write — small N stated plainly; one agent configuration; graders are
themselves LLMs; next steps.)*

## References

- Mitchener L, Laurent JM, Andonian A, et al. **BixBench: a Comprehensive
  Benchmark for LLM-based Agents in Computational Biology.** arXiv, 2025.
  [arXiv:2503.00096](https://arxiv.org/abs/2503.00096).
  doi:[10.48550/arXiv.2503.00096](https://doi.org/10.48550/arXiv.2503.00096)
- Laurent JM, Janizek JD, Ruzo M, et al. **LAB-Bench: Measuring Capabilities of
  Language Models for Biology Research.** arXiv, 2024.
  [arXiv:2407.10362](https://arxiv.org/abs/2407.10362)
- Laurent JM, Bou A, Pieler M, et al. **LABBench2: An Improved Benchmark for AI
  Systems Performing Biology Research.** arXiv, 2026.
  [arXiv:2604.09554](https://arxiv.org/abs/2604.09554)
- Chen Z, et al. **ScienceAgentBench: Toward Rigorous Assessment of Language
  Agents for Data-Driven Scientific Discovery.** ICLR 2025.
  [arXiv:2410.05080](https://arxiv.org/abs/2410.05080)
