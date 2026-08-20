# Design decision: which model, in which role

Two independent choices hide behind "use Claude": the model that *does the
analysis* (the agent under test) and the model that *judges the answer* (the
grader). They can be set separately, and the tradeoffs differ.

## What the harness actually does

`scripts/run_zeroshot.sh` passes `--model` to `generate_zeroshot_evals.py`, which
sets the **answering** model. It then calls `grade_outputs.py` with no `--model`,
so grading always falls back to the default: **`gpt-4o` at temperature 1.0**.

The shipped baseline filenames are therefore misnamed.
`claude-3-5-sonnet-latest-grader-openended.csv` does not mean "graded by Claude";
it means "answered by Claude, graded by gpt-4o".

This produces an asymmetry in BixBench's published comparison:

| Baseline | Answerer | Grader | Self-graded? |
|---|---|---|---|
| `gpt-4o-grader-*` | gpt-4o | gpt-4o | **yes** |
| `claude-3-5-sonnet-latest-grader-*` | claude-3-5-sonnet | gpt-4o | no |

If LLM judges favor their own outputs at all, that bias flatters gpt-4o and only
gpt-4o. Worth stating in the writeup regardless of which option below is taken —
it costs nothing to observe and no other BixBench commentary appears to note it.

## The agent: Claude

Uncontroversial. `claude_image.yaml` and `claude_no_image.yaml` are shipped
configs, so a Claude agent is one of the four the paper ran. No methodological
cost.

## The grader: the actual decision

### Option A — Claude grades Claude

| | |
|---|---|
| Cost | One provider, one key |
| Loses | Comparability to published numbers (which are all gpt-4o-graded) |
| Risk | Self-preference: Claude judging Claude's own answers |

The self-preference risk is **much smaller for this study than it would be for an
accuracy claim**. The headline is self-consistency across replicates — whether
the agent contradicts itself. A grader with a constant bias toward one style
shifts the accuracy *level*; it does not manufacture *inconsistency*. So:

- **Q1 (reliability) is largely robust** to this bias.
- **Q2 (accuracy posterior) is not** — the level would be biased upward, and any
  stated accuracy would need an explicit caveat.

### Option B — gpt-4o grades Claude (the harness default)

Matches the shipped configuration exactly, so results sit alongside published
numbers. No self-preference confound. Requires an OpenAI key.

### Option C — grade the same answers with both

The agent runs are the expensive half and are **shared**: the agent runs once,
its stored answers are graded twice. Measured grading cost is ~$0.81 for a full
K=20 sweep, so the marginal cost of a second grader is under a dollar.

This converts the limitation into a third result: **how often two frontier
graders disagree about the same answer**. That is a distinct noise source from
agent noise and grader-resampling noise, and it is arguably the most interesting
number in the whole study — a benchmark whose graders disagree with each other
has a ceiling on how precisely it can rank anything.

## Recommendation

**Agent: Claude.** Settled, no downside.

**Grader: Option C if an OpenAI key is obtainable, Option A if not.**

The reasoning is cost asymmetry. Grading is nearly free relative to agent runs,
and the answers being graded are identical, so a second grader buys a whole
additional finding for pocket change. Claude can still be the *primary* grader,
with gpt-4o as the control.

If only Claude is available, the study is still sound — but the writeup should
scope its claims to **consistency rather than accuracy level**, and say plainly
that the grader shares a model family with the agent.

## Aims by option

| | Option A (Claude only) | Option C (both graders) |
|---|---|---|
| Lead finding | Agent self-consistency across replicates at temperature 1.0 | Same |
| Grader-noise control | Claude regrading identical answers K times | Both graders, separately |
| Third finding | — | Cross-grader disagreement rate |
| Accuracy claim | Caveated; self-preference unquantified | Clean, comparable to published |
| Extra cost | $0 | < $1 |
| Extra complexity | None | One more API key |

---

# Quantifying self-preference (Option C, chosen)

## The identification problem

With a Claude agent and two graders, a raw gap between them is not
self-preference. If the Claude grader marks Claude's answers correct more often
than the gpt-4o grader does, that is consistent with either:

- **self-preference** — the grader favors its own family's style, or
- **leniency** — the Claude grader is simply a softer marker on everything.

One answer set cannot separate those. The leniency effect and the
self-preference effect are perfectly confounded.

## The fix: a 2x2, which is nearly free here

Cross two answer sets with two graders:

| | gpt-4o grader | Claude grader |
|---|---|---|
| **gpt-4o answers** | A — self | B — cross |
| **Claude answers** | C — cross | D — self |

Self-preference is the **interaction**, a difference in differences:

```
self_preference = (A - B) - (C - D)
```

- A grader that is uniformly lenient raises A and C together → cancels.
- An answer set that is simply better raises A and B together → cancels.
- What survives is model-specific favoritism.

**The expensive half already exists.** The repo ships both answer sets as
zero-shot baselines — `gpt-4o-grader-openended.csv` (gpt-4o's answers) and
`claude-3-5-sonnet-latest-grader-openended.csv` (Claude 3.5's answers), 205 rows
each. No agent runs are needed to fill the grid; only grading calls.

## Cost

4 cells x 203 LLM-graded questions x K replicates, split evenly between graders:

| K | Calls per grader | Total | Approx cost |
|---:|---:|---:|---:|
| 10 | 4,060 | 8,120 | ~$5 |
| 20 | 8,120 | 16,240 | ~$10 |

Replicates are needed in every cell regardless, because the grader-noise floor
has to be estimated per cell — the shipped baselines are single draws.

## The model

This maps onto the `brms` work already planned for Q2, so the statistical
machinery does double duty:

```r
brm(
  correct ~ answerer * grader + (1 | capsule / question),
  family = bernoulli(),
  ...
)
```

The `answerer:grader` interaction coefficient **is** the self-preference
estimate, on the log-odds scale, with a posterior credible interval rather than a
point estimate. Varying intercepts for capsule and question absorb the fact that
some questions are simply harder, and handle the repeated grading of the same
question across replicates rather than treating those draws as independent.

## Caveats to state plainly

- **These are zero-shot baselines**, produced without notebook execution. Grader
  self-preference measured on them may not transfer identically to agentic
  answers, which are longer and carry analysis context. Same questions and same
  grading prompts, though, so it is the right first estimate.
- **Family, not strict self.** If a current Claude model grades Claude 3.5
  Sonnet's answers, that measures *family* preference across generations, not one
  model preferring its own exact outputs. Say so; do not call it self-preference
  without the qualifier.
- **The two answer sets differ in content.** The difference-in-differences
  handles main effects, but not a hypothetical interaction between answer *style*
  and grader that is unrelated to model identity. Acknowledge as a limitation
  rather than claiming clean identification.
- **Extension, once the agent runs exist:** add the Claude agent's own answers as
  a third answer set. That gives true within-model self-preference for the model
  actually under test, at no extra agent cost since those runs are needed anyway.
