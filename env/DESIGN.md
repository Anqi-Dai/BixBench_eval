# Design decision: which model, in which role

Two independent choices hide behind "use Claude": the model that *does the
analysis* (the agent under test) and the model that *judges the answer* (the
grader). They can be set separately, and the tradeoffs differ.

## What the harness actually does

Two grading paths ship, and they do **not** use the same grader. Verified against
`Future-House/BixBench` @ `4931118`.

### Zero-shot path — one grader for both models

`scripts/run_zeroshot.sh` passes `--model` to `generate_zeroshot_evals.py`, which
sets the **answering** model. It then calls `grade_outputs.py` with no `--model`,
so grading falls back to the default: **`gpt-4o` at temperature 1.0**
(`grade_outputs.py:37,40`).

Both answer sets are therefore graded by gpt-4o. The shipped baseline filenames
are misnamed: `claude-3-5-sonnet-latest-grader-openended.csv` does not mean
"graded by Claude"; it means "answered by Claude, graded by gpt-4o".

| Zero-shot baseline | Answerer | Grader | Self-graded? |
|---|---|---|---|
| `gpt-4o-grader-*` | gpt-4o | gpt-4o | **yes** |
| `claude-3-5-sonnet-latest-grader-*` | claude-3-5-sonnet | gpt-4o | no |

Asymmetric: any self-preference flatters gpt-4o and only gpt-4o.

### Agentic path — every model grades itself

The agentic runs are graded somewhere else entirely. `run_agentic.sh` calls
`postprocessing.py`, which calls `postprocessing_utils.run_eval_loop`. That
function picks the grader by **substring-matching the run name**
(`postprocessing_utils.py:62-84`):

```python
models = {
    "4o": "gpt-4o",
    "claude": "claude-3-5-sonnet-20241022",
}
batch = eval_df.loc[eval_df.run_name.str.contains(model_key), "content"].tolist()
```

Run names are `4o_image`, `4o_no_image`, `claude_image`, `claude_no_image`, so
gpt-4o's trajectories are graded by gpt-4o and Claude's by Claude. This holds for
both eval modes — open-answer (`OPEN_ENDED_EVAL_PROMPT`, a binary 0/1 equivalence
judgment) and MCQ (`MCQ_EVAL_PROMPT`, which additionally shows the judge the
notebook).

| Agentic run | Answerer | Grader | Self-graded? |
|---|---|---|---|
| `4o_image`, `4o_no_image` | gpt-4o | gpt-4o | **yes** |
| `claude_image`, `claude_no_image` | claude-3-5-sonnet | claude-3-5-sonnet | **yes** |

Symmetric — but symmetric self-grading is not the same as no self-preference. It
means **every headline agentic number in the paper is self-graded**. The bias, if
it exists, is in all of them rather than in one.

No temperature is passed on this path:
`litellm.acompletion(model=model, messages=message)` takes the provider default.

### The consequence for the paper's main comparison

`run_comparison` in `v1.5_paper_results.yaml` sets `use_zero_shot_baselines: true`
and maps the zero-shot CSVs onto the same run names as the agentic runs, so both
are drawn on the same axes. Combining the two tables above:

| Comparison drawn | Baseline grader | Agentic grader | Grader held constant? |
|---|---|---|---|
| gpt-4o: zero-shot vs agentic | gpt-4o | gpt-4o | yes |
| Claude: zero-shot vs agentic | gpt-4o | claude-3-5-sonnet | **no** |

The Claude agentic-versus-baseline delta is confounded with a change of grader.
The gpt-4o one is not. Worth stating in the writeup regardless of which option
below is taken — it costs nothing to observe and no other BixBench commentary
appears to note it.

### Practical trap for this study's own runs

`run_name` is a free-text field in the run-configuration YAML (`claude_image.yaml`
ends with `run_name: claude_image`), and the grader is selected by `str.contains`
over that string. A replicate run named without `claude` or `4o` in it is
**silently never graded** — `llm_answer` stays `None` and those rows drop out.
Any custom run config for this study must keep the substring, or grading has to
be invoked directly rather than through `postprocessing.py`.

## The agent: Claude

Uncontroversial. `claude_image.yaml` and `claude_no_image.yaml` are shipped
configs, so a Claude agent is one of the four the paper ran. No methodological
cost.

## The grader: the actual decision

### Option A — Claude grades Claude

| | |
|---|---|
| Cost | One provider, one key |
| Matches | **The shipped agentic configuration exactly** — this is what the paper did |
| Risk | Self-preference: Claude judging Claude's own answers |

**This inverts the earlier reading of Option A.** This study runs the agentic
path, and on that path the shipped grader is model-matched. Claude grading Claude
is therefore not a deviation from the benchmark — it reproduces it. Option A
gains comparability to the published agentic numbers rather than losing it.

The self-preference risk is unchanged, and is **much smaller for this study than it would be for an
accuracy claim**. The headline is self-consistency across replicates — whether
the agent contradicts itself. A grader with a constant bias toward one style
shifts the accuracy *level*; it does not manufacture *inconsistency*. So:

- **Q1 (reliability) is largely robust** to this bias.
- **Q2 (accuracy posterior) is not** — the level would be biased upward, and any
  stated accuracy would need an explicit caveat.

### Option B — gpt-4o grades Claude

Matches the *zero-shot* default, not the agentic one. Breaking the self-grading
loop makes it the cleaner instrument, and there is no self-preference confound —
but it reproduces no shipped configuration for agentic runs, so its numbers do
not sit directly alongside the paper's agentic bars. Requires an OpenAI key.

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

Two reasons, and the second is stronger than it was before the agentic grading
path was traced.

**Cost asymmetry.** Grading is nearly free relative to agent runs, and the
answers being graded are identical, so a second grader buys a whole additional
finding for pocket change.

**Claude is the *primary* grader on the merits, not as a fallback.** It is what
the shipped agentic configuration uses, so Claude-graded results are the ones
comparable to the paper's agentic numbers. gpt-4o is then the control that breaks
the self-grading loop — the deviation, deliberately introduced, rather than the
reference.

If only Claude is available, the study is still sound and still reproduces the
shipped setup — but the writeup should scope its claims to **consistency rather
than accuracy level**, and say plainly that the grader shares a model family with
the agent, exactly as the paper's own agentic numbers do.

## Aims by option

| | Option A (Claude only) | Option C (both graders) |
|---|---|---|
| Lead finding | Agent self-consistency across replicates at temperature 1.0 | Same |
| Grader-noise control | Claude regrading identical answers K times | Both graders, separately |
| Third finding | — | Cross-grader disagreement rate |
| Matches shipped agentic setup | Yes | Yes, plus a control arm |
| Accuracy claim | Comparable to the paper's agentic numbers, but self-preference unquantified | Self-preference quantified; both grader regimes reported |
| Extra cost | $0 | < $1 |
| Extra complexity | None | One more API key |

---

# Quantifying self-preference (Option C, chosen)

**Why this matters more than it first appeared.** Before the agentic grading path
was traced, self-preference looked like a limitation of *this study's* grader
choice. It is more than that: because every agentic run in BixBench is graded by
its own model, self-preference — if real — is baked into every headline number
the paper reports, not just into a design decision made here. Measuring it is
therefore a result about the benchmark, not a caveat about the replication.

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
