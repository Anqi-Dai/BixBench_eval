"""Run the BixBench agent on selected capsules, with token accounting.

The upstream harness has no way to restrict a run to particular capsules: its
`load_bixbench` pulls the whole dataset and downloads all 64 capsule zips before
anything else happens. This subclasses the generator to filter first and download
only what is needed, which keeps a single-capsule pricing run from fetching the
entire benchmark.

It also registers a LiteLLM callback so real prompt and completion token counts
are accumulated across every model call the agent makes. Agent cost is the one
number in this project big enough to threaten the timebox, and it needs to be
measured rather than estimated.

Everything else is left to the harness. The agent, rollout and grading behavior
are exactly what the shipped configuration specifies.

Usage:
    python py/run_agent.py --capsule bix-8 --replica 0 \
        --config py/config/pricing_bix8.yaml
"""

import argparse
import asyncio
import csv
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

UPSTREAM = Path(__file__).resolve().parent.parent.parent / "BixBench-upstream"
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(UPSTREAM))

import litellm  # noqa: E402
from bixbench.generate_trajectories import TrajectoryGenerator  # noqa: E402

# Accumulated across every model call the agent makes during the run. LiteLLM
# invokes the callback once per completion, so this ends up counting the agent's
# whole trajectory rather than a single request.
USAGE = {"calls": 0, "prompt": 0, "completion": 0}


def _track(kwargs, response, start_time, end_time):
    u = getattr(response, "usage", None)
    if u is None:
        return
    USAGE["calls"] += 1
    USAGE["prompt"] += getattr(u, "prompt_tokens", 0) or 0
    USAGE["completion"] += getattr(u, "completion_tokens", 0) or 0


# Both hooks are registered because the harness drives the model asynchronously,
# and LiteLLM dispatches sync and async completions to different callback lists.
litellm.success_callback = [_track]
litellm._async_success_callback = [_track]

# USD per million tokens, list pricing.
PRICES = {"anthropic/claude-sonnet-4-5-20250929": (3.00, 15.00)}


class FilteredGenerator(TrajectoryGenerator):
    """Trajectory generator restricted to a chosen set of capsules."""

    def __init__(self, config_path, replica_id, capsules):
        super().__init__(config_path, replica_id)
        self.capsules = set(capsules)

    async def load_bixbench(self):
        """Filter to the requested capsules before any capsule data is fetched.

        The parent method downloads and unpacks every capsule zip in the dataset
        as its first act, so filtering afterwards would still pull ~64 archives.
        Reproducing the load here, with the filter applied first, keeps a
        one-capsule run to one download.
        """
        import datasets

        rows = datasets.load_dataset(
            self.config.paths.hf_repo_id, split=self.config.dataset_split
        ).to_list()
        kept = [r for r in rows if r["short_id"] in self.capsules]
        if not kept:
            sys.exit(f"no questions matched capsules: {sorted(self.capsules)}")
        print(f"selected {len(kept)} questions from {sorted({r['short_id'] for r in kept})}")

        # Force a single batch. The harness's run loop steps by `batch_size` but
        # slices `bixbench[i : i + 4*batch_size]`, so consecutive batches overlap
        # and questions are rolled out several times each -- about 3.3x the
        # necessary work at the shipped batch_size of 24 over 205 questions.
        #
        # The duplicates are worse than wasted spend. Each rollout reuses the same
        # working directory, and fhda's NotebookEnv reloads any notebook it finds
        # there (notebook_env.py:48). So a repeat rollout resumes from the previous
        # attempt's finished notebook, typically submits within one action, and
        # overwrites the clean trajectory. Sizing the batch to cover every question
        # makes the loop run once and keeps each trajectory an independent draw.
        self.config.rollout.batch_size = max(len(kept), 1)
        print(f"batch_size set to {self.config.rollout.batch_size} "
              f"to avoid overlapping-batch reruns")

        # Fetch only the archives the kept questions actually reference.
        zips = {r["data_folder"] for r in kept}
        await asyncio.gather(*(self.process_capsule_data(z) for z in zips))
        await asyncio.gather(*(self.process_question(r) for r in kept))
        return kept


async def main_async(args):
    load_dotenv(UPSTREAM / ".env")
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set")

    # The harness resolves every configured path relative to the working
    # directory, so the run happens from the upstream clone.
    os.chdir(UPSTREAM)

    gen = FilteredGenerator(REPO / args.config, args.replica, args.capsules)
    started = time.time()
    await gen.run()
    elapsed = time.time() - started

    model = gen.config.agent.agent_kwargs["llm_model"]["name"]
    pin, pout = PRICES.get(model, (0.0, 0.0))
    cost = USAGE["prompt"] / 1e6 * pin + USAGE["completion"] / 1e6 * pout

    print(f"\n{'='*60}")
    print(f"capsules      : {', '.join(args.capsules)}   replica {args.replica}")
    print(f"model         : {model}")
    print(f"wall clock    : {elapsed/60:.1f} min")
    print(f"model calls   : {USAGE['calls']:,}")
    print(f"tokens        : {USAGE['prompt']:,} in / {USAGE['completion']:,} out")
    print(f"COST          : ${cost:.4f}")
    print(f"{'='*60}")

    ledger = REPO / "results/spend_log.csv"
    new = not ledger.exists()
    with ledger.open("a", newline="") as fh:
        w = csv.writer(fh)
        if new:
            w.writerow(["run", "model", "calls", "prompt_tokens",
                        "completion_tokens", "usd", "basis"])
        w.writerow([f"agent_{'_'.join(args.capsules)}_rep{args.replica}", model,
                    USAGE["calls"], USAGE["prompt"], USAGE["completion"],
                    f"{cost:.4f}", "actual"])
    print(f"logged to {ledger}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capsules", nargs="+", default=["bix-8"])
    ap.add_argument("--replica", type=int, default=0)
    ap.add_argument("--config", default="py/config/pricing_bix8.yaml")
    asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    main()
