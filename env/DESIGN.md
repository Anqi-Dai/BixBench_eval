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
