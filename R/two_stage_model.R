# Two-stage Bayesian model of agent performance (Phase 3, main finding).
#
# The outcome has three states — no answer, wrong answer, right answer — and
# collapsing them would reproduce the defect this project documents. So we fit
# two hurdle-style stages:
#   stage 1: did the agent produce an answer at all?      (all 140 runs)
#   stage 2: given an answer, was it graded correct?      (130 answered runs)
# Both are intercept-only Bernoulli models with nested random intercepts
# (question within capsule). See HANDOFF.md "What is left" for the rationale;
# the known non-response mechanism (Bioconductor install trap) is reported
# narratively in env/REVIEW_REPORT.md, not as a covariate, because with 3
# capsules a needs-Bioc flag is perfectly confounded with capsule identity.
#
# Run:  Rscript R/two_stage_model.R
# Outputs: results/fits/*.rds (fitted models), results/two_stage_summary.txt

library(tidyverse)
library(brms)

# Reproducibility: one seed for every sampler call.
SEED <- 42

# ---------------------------------------------------------------------------
# 1. Assemble the analysis dataset
# ---------------------------------------------------------------------------

# One row per agent run (question x replicate). Keep only the three K=10
# capsules; the 19 K=1 pilot rows from other capsules can't inform
# replicate-level variation.
runs <- read_csv("results/agent_runs.csv", show_col_types = FALSE) |>
  filter(capsule %in% c("bix-8", "bix-49", "bix-26")) |>
  transmute(
    capsule,
    question = question_id,
    replica,
    # uuid matches the grader files' key, e.g. "bix-26-q3_replica_0"
    uuid = str_c(question_id, "_replica_", replica),
    responded = has_answer
  )

# Grader verdicts: 10 grading replicates per answer per grader. Define an
# answer's `correct` as the grader's majority vote over its 10 replicates,
# so a single flaky grading call can't flip the outcome. We carry all three
# graders: gpt-5 (primary), claude-sonnet-4-5, and gpt-4o (the benchmark's
# default, kept as a sensitivity because it self-contradicts on 14.6% of
# answers — see HANDOFF.md finding 2).
grades <- bind_rows(
  read_csv("results/grader_noise_agent.csv", show_col_types = FALSE),
  read_csv("results/grader_noise_gpt5.csv",  show_col_types = FALSE)
) |>
  mutate(grader = case_when(
    str_detect(grader, "gpt-5")   ~ "gpt5",
    str_detect(grader, "gpt-4o")  ~ "gpt4o",
    str_detect(grader, "claude")  ~ "claude"
  )) |>
  summarise(
    votes_correct = sum(correct),
    n_votes       = n(),
    .by = c(uuid, grader)
  ) |>
  mutate(correct = votes_correct > n_votes / 2)

# One known 5-5 tie exists: gpt-4o on bix-8-q5_replica_3 (both current
# graders call it correct 10/10). The strict `> n/2` rule above counts a tie
# as not correct — the harsher reading of a maximally self-contradicting
# grader. It affects only the gpt-4o sensitivity model, by one answer.
# Report any tie so a new one can't slip in silently.
ties <- filter(grades, votes_correct * 2 == n_votes)
if (nrow(ties) > 0) {
  message("Grader vote ties (counted as not correct): ",
          str_c(ties$uuid, " [", ties$grader, "]", collapse = ", "))
}

# Wide table: one correctness column per grader, joined onto the runs.
d <- grades |>
  pivot_wider(id_cols = uuid, names_from = grader,
              values_from = correct, names_prefix = "correct_") |>
  right_join(runs, by = "uuid")

# Sanity checks before burning sampler time: 140 runs, every answered run has
# a verdict from every grader, every unanswered run has none.
stopifnot(
  nrow(d) == 140,
  sum(d$responded) == 130,
  !anyNA(d$correct_gpt5[d$responded]),
  all(is.na(d$correct_gpt5[!d$responded]))
)

# Persist the assembled dataset so downstream scripts (R/figures.R) use
# exactly the rows and verdicts the models were fit on.
write_csv(d, "results/model_data.csv")

# ---------------------------------------------------------------------------
# 2. Priors
# ---------------------------------------------------------------------------

# Three capsules cannot identify a capsule-level SD from data alone, so the
# prior on the group SDs does real work and must be stated explicitly:
# normal(0, 1.5), half by construction (SDs are positive). On the log-odds
# scale this allows large group differences without endorsing degenerate
# ones. The intercept prior is wide but proper.
priors <- c(
  prior(normal(0, 1.5), class = "Intercept"),
  prior(normal(0, 1.5), class = "sd")
)

fit_dir <- "results/fits"
dir.create(fit_dir, showWarnings = FALSE, recursive = TRUE)

# Shared sampler settings: small hierarchical Bernoulli models with few
# groups are prone to divergences, so raise adapt_delta.
fit_stage <- function(formula, data, name) {
  brm(
    formula, data = data, family = bernoulli(),
    prior = priors,
    # cmdstanr backend: the CRAN rstan binary is ABI-incompatible with
    # RcppParallel >= 6 (oneTBB) on this machine and fails to load compiled
    # models.
    backend = "cmdstanr",
    chains = 4, iter = 4000, warmup = 1000,
    control = list(adapt_delta = 0.99),
    seed = SEED,
    file = file.path(fit_dir, name), file_refit = "on_change"
  )
}

# ---------------------------------------------------------------------------
# 3. Fit the two stages
# ---------------------------------------------------------------------------

# Stage 1 — response: all 140 runs. Non-response is a run-level event (the
# Bioconductor install trap fires stochastically at temperature 1.0), so the
# Bernoulli-with-question-intercepts shape is right.
fit_responded <- fit_stage(
  responded ~ 1 + (1 | capsule / question), d, "stage1_responded"
)

# Stage 2 — correctness given a response, under the primary (gpt-5) grader.
# Subsetting to responded rows is the hurdle conditioning.
d_answered <- filter(d, responded)
fit_correct <- fit_stage(
  correct_gpt5 ~ 1 + (1 | capsule / question), d_answered, "stage2_correct_gpt5"
)

# Sensitivity — same model under the benchmark's default grader (gpt-4o),
# whose verdicts differ from the current models on 19/130 answers.
fit_correct_4o <- fit_stage(
  correct_gpt4o ~ 1 + (1 | capsule / question), d_answered, "stage2_correct_gpt4o"
)

# ---------------------------------------------------------------------------
# 4. Report
# ---------------------------------------------------------------------------

# Posterior of the population rate for a *typical* question: inverse-logit of
# the intercept. (Averaging over the random effects instead would give the
# marginal rate; with logit links the two differ, and "typical question" is
# the quantity the writeup discusses.)
typical_rate <- function(fit) {
  as_draws_df(fit)$b_Intercept |> plogis() |>
    quantile(c(.5, .025, .975)) |> round(3)
}

# Per-question partially pooled rates with 95% intervals, on new data with one
# row per question so each question's own intercept is used.
question_rates <- function(fit, data) {
  nd <- distinct(as_tibble(data), capsule, question)
  ep <- posterior_epred(fit, newdata = nd)
  nd |>
    mutate(
      rate  = apply(ep, 2, median),
      lo95  = apply(ep, 2, quantile, .025),
      hi95  = apply(ep, 2, quantile, .975),
      n_obs = map2_int(capsule, question,
                       \(c, q) sum(data$capsule == c & data$question == q))
    ) |>
    mutate(across(c(rate, lo95, hi95), \(x) round(x, 3)))
}

# Write everything the writeup needs into one text file, plus keep the fitted
# models on disk for later post-processing.
sink("results/two_stage_summary.txt")
cat("Two-stage model summary —", format(Sys.time()), "\n")
cat("Data: 140 runs (3 capsules x 10 replicates), 130 answered.\n\n")

fits <- list(
  "stage 1: responded (all 140 runs)"          = fit_responded,
  "stage 2: correct | responded, gpt-5 grader" = fit_correct,
  "sensitivity: correct, gpt-4o grader"        = fit_correct_4o
)
for (label in names(fits)) {
  fit <- fits[[label]]
  cat("==========", label, "==========\n")
  print(summary(fit))
  cat("\nTypical-question rate (median [95% CI]):\n")
  print(typical_rate(fit))
  cat("\nPer-question partially pooled rates:\n")
  print(question_rates(fit, fit$data |>
    mutate(capsule = as.character(capsule), question = as.character(question))),
    n = 20)
  cat("\n")
}
sink()

message("Done. Summary: results/two_stage_summary.txt; fits: results/fits/")
