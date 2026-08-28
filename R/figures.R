# Figures for the two-stage model findings (Phase 3 / writeup).
#
# One figure per conclusion, titled with the conclusion itself
# (assertion-evidence style), so each can stand alone in the writeup or a
# LinkedIn post. Ordered so each figure licenses the next:
#   fig1 — the choice of grader flips whole questions, not scattered answers
#          (so "correct" is a measured quantity; gpt-5 is the primary grader
#          everywhere downstream)
#   fig2 — the outcome has three states; refusals/no-answers are not wrong answers
#   fig3 — given an answer, correctness is a property of the question, not luck
#   fig4 — the incorrect runs, split by verified cause
#
# Colors follow the dataviz reference palette (documented passing sets, light
# mode): categorical slots 1-3 for capsule identity, status good/critical for
# right/wrong with the muted chrome gray for "no answer". Every colored
# segment is also direct-labeled, so meaning never rides on color alone.
#
# Run after R/two_stage_model.R:  Rscript R/figures.R
# Outputs: results/figures/fig{1,2,3,4}_*.png (300 dpi) and matching .pdf

library(tidyverse)
library(brms)
library(ggtext)

# ---- palette and shared theme ---------------------------------------------

# Reference-palette hexes (light mode). The capsule trio is the palette's
# documented all-pairs-passing categorical opening; status colors carry the
# right/wrong semantics and are never reused as series colors.
PAL <- list(
  capsule = c("bix-8" = "#2a78d6", "bix-49" = "#eb6834", "bix-26" = "#1baf7a"),
  good     = "#0ca30c",  # graded correct
  critical = "#d03b3b",  # graded incorrect
  noanswer = "#898781",  # no answer submitted (neutral, not a judgment)
  ink      = "#0b0b0b", ink2 = "#52514e", muted = "#898781",
  grid     = "#e1e0d9", surface = "#fcfcfb"
)

# Recessive chrome: hairline grid, no axis lines, ink for text — per the
# marks-and-anatomy spec. Titles are sentences (the conclusion), left-aligned.
theme_viz <- theme_minimal(base_size = 12) +
  theme(
    plot.background = element_rect(fill = PAL$surface, color = NA),
    panel.grid.minor = element_blank(),
    panel.grid.major = element_line(color = PAL$grid, linewidth = .3),
    plot.title = element_text(face = "bold", size = 13, color = PAL$ink),
    plot.subtitle = element_text(color = PAL$ink2, size = 10),
    plot.caption = element_text(color = PAL$muted, size = 8, hjust = 0),
    axis.title = element_text(color = PAL$ink2, size = 10),
    axis.text = element_text(color = PAL$ink2),
    legend.position = "top", legend.justification = "left",
    legend.title = element_blank(),
    strip.text = element_text(face = "bold", color = PAL$ink),
    plot.title.position = "plot", plot.caption.position = "plot"
  )

# Save each figure as PNG (posts, slides) and PDF (print/vector), same size.
save_fig <- function(plot, name, width, height) {
  for (ext in c("png", "pdf")) {
    # cairo_pdf for the vector copy: the base pdf device cannot embed the
    # em-dashes used in subtitles
    dev <- if (ext == "pdf") cairo_pdf else "png"
    ggsave(file.path("results/figures", str_c(name, ".", ext)),
           plot, width = width, height = height, dpi = 300, bg = PAL$surface,
           device = dev)
  }
}
dir.create("results/figures", showWarnings = FALSE, recursive = TRUE)

# ---- data ------------------------------------------------------------------

# The exact dataset the models were fit on (written by R/two_stage_model.R).
d <- read_csv("results/model_data.csv", show_col_types = FALSE)

# Order questions within capsule; capsules ordered by overall difficulty
# (bix-8 best -> bix-26 worst) so all figures read the same way.
capsule_order <- c("bix-8", "bix-49", "bix-26")
d <- d |>
  mutate(
    capsule = factor(capsule, levels = capsule_order),
    question = fct_reorder(question, as.integer(str_extract(question, "[0-9]+$")))
  )

# ---- fig 1: disagreement follows generation, not family ---------------------

# This comes first because every later figure rests on a correct/incorrect
# judgment, and that judgment is itself a measurement with a chooseable
# instrument. Three graders: gpt-5 and claude-sonnet-4-5 are different
# families but the same (current) generation; gpt-4o is gpt-5's own family,
# one generation back. The two current models give identical majority
# verdicts on all 130 answers, while the older family-mate flips whole
# questions — so grader choice is about generation, not vendor, and gpt-5
# stands as the primary grader for figs 2-4.
grader_rates <- d |>
  filter(responded) |>
  summarise(
    `gpt-5`             = mean(correct_gpt5),
    `claude-sonnet-4-5` = mean(correct_claude),
    `gpt-4o (prev gen)` = mean(correct_gpt4o),
    .by = c(capsule, question)
  ) |>
  pivot_longer(-c(capsule, question), names_to = "grader", values_to = "rate") |>
  mutate(
    grader = factor(grader, levels = c("gpt-4o (prev gen)", "claude-sonnet-4-5", "gpt-5")),
    question = fct_reorder(question, as.integer(str_extract(question, "[0-9]+$")))
  ) |>
  # draw order = row order in a single layer: sort large-to-small (the factor
  # levels run gpt-4o > claude > gpt-5 by size) so the big dot never covers
  # the nested smaller ones
  arrange(grader)

# Questions where the previous-generation grader lands far from the current
# pair get direct labels.
flips <- grader_rates |>
  summarise(flip = max(rate) - min(rate) > .5, .by = question) |>
  filter(flip) |> pull(question)

# Concentric sizes, largest drawn first: exact agreement (the common case)
# shows as nested rings instead of one grader's dot hiding the others.
# Dark2 (RColorBrewer) hues chosen to avoid fig3's blue/orange/aqua:
# magenta outer ring, purple middle, mustard center — each ring pair differs
# strongly in hue and lightness so the nesting stays readable
GRADER_COL <- c(`gpt-4o (prev gen)` = "#E7298A",
                `claude-sonnet-4-5` = "#7570B3",
                `gpt-5`             = "#E6AB02")
# sizes spaced so each visible ring is a thick, readable band
GRADER_SIZE <- c(`gpt-4o (prev gen)` = 6.0,
                 `claude-sonnet-4-5` = 3.8,
                 `gpt-5`             = 1.6)

fig1 <- grader_rates |>
  ggplot(aes(rate, fct_rev(question))) +
  geom_line(aes(group = question), color = PAL$grid, linewidth = 1) +
  # open rings (shape 21, transparent fill) instead of solid dots: three
  # diameters, so full overlap still shows all three graders as concentric
  # circles rather than one big filled disc
  geom_point(aes(color = grader, size = grader),
             shape = 21, fill = NA, stroke = 1.8) +
  # selective direct labels, only where the generations part ways
  # labels point inward (toward plot center) and sit just above the
  # connector, so they never clip at the panel edge
  geom_text(data = \(x) filter(x, question %in% flips, grader != "gpt-5"),
            aes(label = if_else(grader == "gpt-4o (prev gen)",
                                "gpt-4o", "gpt-5 & claude"),
                color = grader,
                hjust = if_else(rate > .5, 1.35, -0.35)),
            nudge_y = 0.55, size = 3, fontface = "bold",
            show.legend = FALSE) +
  facet_grid(capsule ~ ., scales = "free_y", space = "free_y") +
  scale_color_manual(values = GRADER_COL) +
  scale_size_manual(values = GRADER_SIZE) +
  # legend dots at a uniform readable size; identity in the plot itself is
  # carried by the nesting order, not dot size
  guides(color = guide_legend(override.aes = list(size = 3, stroke = 1.8)),
         size = "none") +
  scale_x_continuous(limits = c(-.06, 1.06), breaks = c(0, .5, 1),
                     labels = c("0%", "50%", "100%")) +
  labs(
    title = "Grader disagreement follows model generation, not model family",
    subtitle = "Share of answered runs graded correct per question (majority of 10 grading replicates per grader).\ngpt-5 and claude-sonnet-4-5 — different families, current generation — agree on all 130 answers (nested dots);\ngpt-4o — BixBench's default grader, one generation behind its own family-mate — flips whole questions.",
    x = "runs graded correct", y = NULL,
    caption = "Same 130 answers under all three graders. gpt-5 is the primary grader for the remaining figures."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank())
save_fig(fig1, "fig1_grader_flips", 7.5, 6.6)

# ---- fig 2: three outcome states per question ------------------------------

# Collapse each run to one of three states under the primary (gpt-5) grader.
# The gray band is what a binary score silently counts as "wrong". One
# addition, matching the section text's 9-vs-1 attribution: the single
# no-answer run that is the agent's own doing (bix-26-q4 replica 9 ran out
# of its 40-step budget) is hatched; the other nine gray runs died in the
# harness's own Bioconductor install trap (env/REVIEW_REPORT.md).
library(ggpattern)

states <- d |>
  mutate(
    state = case_when(
      !responded    ~ "no answer",
      correct_gpt5  ~ "correct",
      TRUE          ~ "incorrect"
    ) |> factor(levels = c("correct", "incorrect", "no answer")),
    side = if_else(!responded & question == "bix-26-q4" & replica == 9,
                   "agent", "none"),
    combo = factor(
      str_c(state, "/", side),
      levels = c("correct/none", "incorrect/none",
                 "no answer/none", "no answer/agent")
    )
  ) |>
  count(capsule, question, state, side, combo)

fig2 <- states |>
  ggplot(aes(n, fct_rev(question))) +
  # 2px surface gap between stacked segments; the hatch appears on exactly
  # one segment, so the legend entry has to say what it means concretely
  geom_col_pattern(
    aes(fill = state, pattern = side, group = combo),
    width = .62, color = PAL$surface, linewidth = .7,
    pattern_fill = NA, pattern_colour = "white", pattern_alpha = .8,
    pattern_angle = 45, pattern_density = .001, pattern_spacing = .05,
    pattern_size = .25, pattern_key_scale_factor = .45
  ) +
  # direct label: count inside each segment, so color never carries the
  # meaning alone
  geom_text(aes(label = n, group = combo),
            position = position_stack(vjust = .5),
            color = "black", size = 3, fontface = "bold") +
  facet_grid(capsule ~ ., scales = "free_y", space = "free_y") +
  scale_fill_manual(values = c(correct = PAL$good, incorrect = PAL$critical,
                               `no answer` = PAL$noanswer),
                    guide = guide_legend(order = 1,
                                         override.aes = list(pattern = "none"))) +
  scale_pattern_manual(values = c(none = "none", agent = "stripe"),
                       breaks = "agent",
                       labels = c(agent = "ran out of steps (agent's own)")) +
  guides(pattern = guide_legend(order = 2,
                                override.aes = list(fill = PAL$noanswer))) +
  scale_x_continuous(breaks = seq(0, 10, 2), expand = expansion(mult = c(0, .02))) +
  labs(
    title = "An agent run has three outcomes, not two",
    subtitle = "10 replicate runs per question (claude-sonnet-4-5, temp 1.0); correctness by gpt-5 majority vote.\nBixBench scores every run correct/incorrect only, so it counts the gray no-answer runs as incorrect answers.",
    x = "runs (of 10)", y = NULL,
    caption = "BixBench: 3 capsules covering 14 questions, 10 replicate runs each = 140 runs."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank(),
                    legend.text = element_text(size = 8.5))
save_fig(fig2, "fig2_three_states", 7.5, 4.8)

# ---- fig 3: posterior per-question correctness (bimodal) -------------------

# Partially pooled posterior rates from the stage-2 model: median + 95%
# interval per question, answered runs only. Stage 1's P(answered) panel was
# dropped deliberately — it restates fig 2's no-answer pattern, and the
# section's argument only needs the correctness stage.
fit_correct <- readRDS("results/fits/stage2_correct_gpt5.rds")

# posterior_epred on one row per question gives that question's own pooled
# rate; summarize to median and 95% interval.
post <- {
  nd <- distinct(as_tibble(fit_correct$data), capsule, question)
  ep <- posterior_epred(fit_correct, newdata = nd)
  nd |> mutate(
    rate = apply(ep, 2, median),
    lo = apply(ep, 2, quantile, .025),
    hi = apply(ep, 2, quantile, .975)
  )
} |>
  mutate(
    capsule = factor(capsule, levels = capsule_order),
    question = fct_reorder(question, as.integer(str_extract(question, "[0-9]+$")))
  )

fig3 <- post |>
  ggplot(aes(rate, fct_rev(question), color = capsule)) +
  # 95% interval as a thin line, median as a >=8px point
  geom_linerange(aes(xmin = lo, xmax = hi), linewidth = .7, alpha = .55) +
  geom_point(size = 2.6) +
  # strip labels rendered in the capsule's own color (ggtext markdown), so
  # the dot colors need no separate legend
  facet_grid(capsule ~ ., scales = "free_y", space = "free_y",
             labeller = labeller(capsule = \(x)
               str_c("<span style='color:", PAL$capsule[x], "'>", x, "</span>"))) +
  scale_color_manual(values = PAL$capsule) +
  scale_x_continuous(limits = c(0, 1), breaks = c(0, .5, 1),
                     labels = c("0", "0.5", "1")) +
  labs(
    title = "Given an answer, correctness is a property of the question, not luck",
    subtitle = "Answered runs only. Each dot is a question's estimated underlying success probability (posterior median,\nhierarchical model); the band is 95% uncertainty about that probability — 10 runs cannot pin it exactly\neven when all 10 agree.",
    x = "estimated probability of a correct answer", y = NULL,
    caption = "Bernoulli GLMMs, question nested in capsule; gpt-5 majority-vote grading. Question-level SD (stage 2): 3.2 log-odds."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank(),
                    legend.position = "none",
                    strip.text.y = element_markdown(face = "bold"))
save_fig(fig3, "fig3_question_rates", 7.5, 4.8)

# ---- fig 4: the incorrect runs, split by verified cause --------------------

# Only fig 2's red state, attributed. Every incorrect run was re-derived —
# both the answer key and the agent's answer — from the raw capsule data
# (env/REVIEW_REPORT.md; every cause verified by recomputation,
# classification decisions dated 2026-08-24). Unhatched red is the
# benchmark's (answer key or question wording); hatched red is the agent's
# own. The no-answer runs' attribution lives in fig 2 and the section text.
#
# Per-trajectory assignment, from the report's review table:
#   - all incorrect bix-49 runs and bix-8-q6/q7 -> answer-key error (hidden
#     sex covariate; transcript/gene conflation)
#   - bix-8-q3 rep 2 -> answer-key error (gene-level answer vs row-level key)
#   - bix-26-q5 reps 0/2/4 (answered 1, the stated-thresholds answer) ->
#     answer-key error (the key skips its own padj filter)
#   - bix-8-q2 rep 0 (2x2) and bix-26-q5 reps 5/9 (GSEA; hand-rolled
#     pathway-LFC) -> ambiguous question
#   - bix-26-q5 reps 1/6/7/8 (the 58s) and bix-26-q4 reps 0/5 -> agent error
# bix-8-q5 (the print-floor key) does not appear: gpt-5 grades those runs
# correct, so that benchmark defect is absorbed by the grader, not visible
# in this figure.

causes <- d |>
  filter(responded, !correct_gpt5) |>
  mutate(
    cause = case_when(
      question == "bix-8-q2"  ~ "ambiguous question",
      question == "bix-26-q5" & replica %in% c(5, 9) ~ "ambiguous question",
      question == "bix-26-q5" & replica %in% c(1, 6, 7, 8) ~ "agent error",
      question == "bix-26-q4" ~ "agent error",
      TRUE ~ "answer-key error"
    ),
    side = factor(if_else(cause == "agent error",
                          "agent's defect", "benchmark's defect"),
                  levels = c("benchmark's defect", "agent's defect"))
  ) |>
  count(capsule, question, side)

# Give every question a row, so the all-correct questions keep their place in
# the row order (all-correct is information too): zero-height bars render
# nothing, and a muted zero marks them instead.
causes <- distinct(d, capsule, question) |>
  left_join(causes, by = c("capsule", "question")) |>
  mutate(side = replace_na(side, "benchmark's defect"), n = replace_na(n, 0L))

zeros <- causes |>
  summarise(total = sum(n), .by = c(capsule, question)) |>
  filter(total == 0)

fig4 <- causes |>
  ggplot(aes(n, fct_rev(question))) +
  # all bars are fig 2's incorrect red; the only encoding is the hatch that
  # marks the agent's share of each bar
  geom_col_pattern(
    aes(pattern = side, group = side),
    fill = PAL$critical,
    width = .62, color = PAL$surface, linewidth = .7,
    pattern_fill = NA, pattern_colour = "white", pattern_alpha = .8,
    pattern_angle = 45, pattern_density = .001, pattern_spacing = .05,
    pattern_size = .25, pattern_key_scale_factor = .45
  ) +
  geom_text(data = \(x) filter(x, n > 0),
            aes(label = n, group = side),
            position = position_stack(vjust = .5),
            color = "black", size = 3, fontface = "bold") +
  geom_text(data = zeros,
            aes(x = .12, y = fct_rev(question), label = "0"),
            inherit.aes = FALSE,
            color = PAL$muted, size = 3, hjust = 0) +
  facet_grid(capsule ~ ., scales = "free_y", space = "free_y") +
  scale_pattern_manual(values = c(`benchmark's defect` = "none",
                                  `agent's defect` = "stripe")) +
  guides(pattern = guide_legend(override.aes = list(fill = PAL$critical))) +
  scale_x_continuous(breaks = seq(0, 10, 2), limits = c(0, 10),
                     expand = expansion(mult = c(0, .02))) +
  labs(
    title = "Most incorrect answers trace to the benchmark; hatching marks the agent's share",
    subtitle = "Every incorrect run attributed by re-deriving both the answer key and the agent's answer from the raw\ncapsule data (env/REVIEW_REPORT.md): 74 of 80 trace to the benchmark — the answer key or the question's\nwording. The 6 hatched runs, all in bix-26, are the agent's own.",
    x = "incorrect runs (of 10)", y = NULL,
    caption = "gpt-5 majority-vote grading. bix-8-q5's print-floor key is absent only because gpt-5 grades p = 8.1e-194 as satisfying \"p < 2.2e-16\"."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank(),
                    legend.text = element_text(size = 8.5))
save_fig(fig4, "fig4_failure_causes", 7.5, 4.8)


message("Wrote figures to results/figures/")
