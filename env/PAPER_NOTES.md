# What the BixBench paper actually says

Verified against arXiv:2503.00096 (v1) rather than recollection, per the brief's
own instruction not to cite remembered figures.

## Headline figures

- **17% accuracy in the open-answer regime** for the best frontier model.
- **No better than random** in the multiple-choice setting.
- Dataset described as "over 50 real-world scenarios" with "nearly 300"
  open-answer questions.

Note the count mismatch with the shipped artifacts (64 capsule zips on the hub,
205 questions across 54 capsules in v1.5 metadata). Cite the paper's numbers as
the paper's, and the v1.5 numbers as v1.5.

## The paper already runs 10 replicates

This is the single most important thing for this project, and it revises the
premise in the brief.

> "To account for stochastic trajectories, we run each analysis in parallel 10
> times to calculate overall performance."

> "we perform 10 parallel iterations of each capsule resulting in the collection
> of 530 trajectories"

So the framing "BixBench reports a single-run point estimate" is **not correct**.
The authors were aware of stochasticity and replicated for it.

What they do with those replicates is where the gap is:

> "Performance on a question is primarily calculated as accuracy, the fraction of
> correct answers given across all parallel runs over all questions provided."

The 10 runs are **pooled into a single fraction**. The paper reports **no standard
deviation, no confidence interval, no error bars, and no measure of how often the
agent answers the same question differently across runs.**

**The variance was generated and then discarded.** That is a sharper and far more
defensible thesis than "they only ran it once", because it cannot be answered with
"we did replicate" — the point is that replication happened and its dispersion was
never reported.

There is a second, statistical consequence. Pooling 10 correlated runs per
question into one fraction treats roughly 2,050 observations as though they were
independent, when they are 205 questions each observed 10 times. Any standard
error computed that way would be badly understated. A varying-intercept model
over capsule and question — already the plan for Q2 — is the direct remedy.

For MCQ the aggregation actively hides inconsistency:

> "we further employ majority voting over the 10 runs to derive a majority-based
> consensus across the iterations."

Majority voting is a variance-suppression device. It converts an unstable answer
into a stable one and reports the stable version.

## The judge model: paper and code disagree

The paper says:

> "The final submitted answer is then automatically evaluated by a judge LLM
> (Claude 3.5 Sonnet) by comparing the agent-generated response against a
> ground-truth solution."

The shipped code says otherwise. `grade_outputs.py` defaults `--model` to
**`gpt-4o`**, and `scripts/run_zeroshot.sh` calls it without `--model`, so every
shipped baseline is graded by gpt-4o.

Either the released code diverged from what produced the paper, or the paper's
description is inaccurate. Worth stating neutrally as a reproducibility
observation, not an accusation — but it does mean **anyone reproducing BixBench
from the repo is using a different judge than the paper describes.**

## What the paper does not discuss

Checked the full text and the repository. Neither mentions:

- judge or grader bias
- self-preference, or a model grading its own outputs
- judge reliability, inter-rater agreement, or judge self-consistency
- human validation of the grader
- limitations of LLM-based grading
- temperature settings (the shipped configs use 1.0)

The repo grep for `self-preference|bias|leniency|judge` returns nothing.

**So the answer is no: the self-preference risk is not raised anywhere.** In the
shipped-code configuration it is live, because the gpt-4o baseline is graded by
gpt-4o while the Claude baseline is graded by gpt-4o — one self-graded, one
cross-graded, compared side by side.
