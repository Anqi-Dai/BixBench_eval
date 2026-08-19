# BixBench Reliability Study

**Status: in progress (Phase 0 — environment).** This README will be rewritten
finding-first once the reliability result is in hand.

## The question

BixBench reports how often LLM agents get bioinformatics analyses right. It does
not report whether those numbers are **stable**, or what the failures actually
are **biologically**.

This is a small, deliberately scoped probe of both:

1. **Reliability.** Run the same agent on the same capsules multiple times at
   non-zero temperature. How often does it contradict itself? A benchmark score
   from a single run is a point estimate of a noisy process.
2. **Uncertainty.** Model accuracy with a Bayesian multilevel model (varying
   intercept per capsule) so a few unusually hard or easy capsules do not distort
   the headline. Posteriors and credible intervals, not bare percentages.
3. **Failure taxonomy.** For capsules near my own domain (microbiome,
   metagenomics, RNA-seq, differential expression, clinical multi-omics), read
   the agent notebooks by hand and classify *how* it failed, not just *that* it did.

## Scope, stated up front

Small N, a subset of capsules, one agent configuration, one model. This is a
structured probe, not a replication of the BixBench leaderboard — that already
exists and is not worth redoing.

## Layout

| Path | What lives here |
|---|---|
| `env/` | Phase 0 environment setup and a running friction log |
| `py/` | Replicate-run pipeline over the BixBench harness |
| `R/` | `brms` multilevel analysis of the results |
| `results/` | Tidy CSV — the handoff from Python to R, and the durable artifact |
| `notebooks/` | Curated agent notebooks quoted in the failure taxonomy |
| `data/` | Capsule data (gitignored; pulled from Hugging Face) |

## Upstream

- Paper: [arXiv:2503.00096](https://arxiv.org/abs/2503.00096) — *BixBench: a Comprehensive Benchmark for LLM-based Agents in Computational Biology*
- Harness: [Future-House/BixBench](https://github.com/Future-House/BixBench)
- Agent: [Future-House/data-analysis-crow](https://github.com/Future-House/data-analysis-crow)
- Dataset: [futurehouse/BixBench](https://huggingface.co/datasets/futurehouse/BixBench) (gated)

## License

MIT — see [LICENSE](LICENSE).
