# Figures for the two-stage model findings (Phase 3 / writeup).
#
# One figure per conclusion, titled with the conclusion itself
# (assertion-evidence style), so each can stand alone in the writeup or a
# LinkedIn post:
#   fig1 — the outcome has three states; refusals/no-answers are not wrong answers
#   fig2 — correctness is a property of the question, not run-to-run luck
#   fig3 — the choice of grader flips whole questions, not scattered answers
#
# Colors follow the dataviz reference palette (documented passing sets, light
# mode): categorical slots 1-3 for capsule identity, status good/critical for
# right/wrong with the muted chrome gray for "no answer". Every colored
# segment is also direct-labeled, so meaning never rides on color alone.
#
# Run after R/two_stage_model.R:  Rscript R/figures.R
# Outputs: results/figures/fig{1,2,3}_*.png (300 dpi) and matching .pdf

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
# (bix-8 best -> bix-26 worst) so both figures read the same way.
capsule_order <- c("bix-8", "bix-49", "bix-26")
d <- d |>
  mutate(
    capsule = factor(capsule, levels = capsule_order),
    question = fct_reorder(question, as.integer(str_extract(question, "[0-9]+$")))
  )

# ---- fig 1: three outcome states per question ------------------------------

# Collapse each run to one of three states under the primary (gpt-5) grader.
# This is the figure that shows why the model is two-stage: the gray band is
# what a binary score would silently count as "wrong".
states <- d |>
  mutate(state = case_when(
    !responded    ~ "no answer",
    correct_gpt5  ~ "correct",
    TRUE          ~ "incorrect"
  ) |> factor(levels = c("correct", "incorrect", "no answer"))) |>
  count(capsule, question, state)

fig1 <- states |>
  ggplot(aes(n, fct_rev(question), fill = state)) +
  # 2px surface gap between stacked segments, thin bars
  geom_col(width = .62, color = PAL$surface, linewidth = .7) +
  # direct label: count inside each segment (white ink on the status fills,
  # so color never carries the meaning alone)
  geom_text(aes(label = n), position = position_stack(vjust = .5),
            color = "white", size = 3, fontface = "bold") +
  facet_grid(capsule ~ ., scales = "free_y", space = "free_y") +
  scale_fill_manual(values = c(correct = PAL$good, incorrect = PAL$critical,
                               `no answer` = PAL$noanswer)) +
  scale_x_continuous(breaks = seq(0, 10, 2), expand = expansion(mult = c(0, .02))) +
  labs(
    title = "An agent run has three outcomes, not two",
    subtitle = "10 replicate runs per question (claude-sonnet-4-5, temp 1.0); correctness by gpt-5 majority vote.\nBixBench scores every run correct/incorrect only, so it counts the gray no-answer runs as incorrect answers.",
    x = "runs (of 10)", y = NULL,
    caption = "BixBench: 3 capsules covering 14 questions, 10 replicate runs each = 140 runs."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank())
save_fig(fig1, "fig1_three_states", 7.5, 4.8)

# ---- fig 2: posterior per-question rates (bimodal correctness) -------------

# Partially pooled posterior rates from the fitted models: median + 95%
# interval per question, for both stages side by side.
fits <- list(
  "P(answered)"            = readRDS("results/fits/stage1_responded.rds"),
  "P(correct | answered)"  = readRDS("results/fits/stage2_correct_gpt5.rds")
)

# posterior_epred on one row per question gives that question's own pooled
# rate; summarize to median and 95% interval.
post <- imap(fits, \(fit, label) {
  nd <- distinct(as_tibble(fit$data), capsule, question)
  ep <- posterior_epred(fit, newdata = nd)
  nd |> mutate(
    stage = label,
    rate = apply(ep, 2, median),
    lo = apply(ep, 2, quantile, .025),
    hi = apply(ep, 2, quantile, .975)
  )
}) |>
  list_rbind() |>
  mutate(
    capsule = factor(capsule, levels = capsule_order),
    stage = factor(stage, levels = names(fits)),
    question = fct_reorder(question, as.integer(str_extract(question, "[0-9]+$")))
  )

fig2 <- post |>
  ggplot(aes(rate, fct_rev(question), color = capsule)) +
  # 95% interval as a thin line, median as a >=8px point
  geom_linerange(aes(xmin = lo, xmax = hi), linewidth = .7, alpha = .55) +
  geom_point(size = 2.6) +
  # strip labels rendered in the capsule's own color (ggtext markdown), so
  # the dot colors need no separate legend
  facet_grid(capsule ~ stage, scales = "free_y", space = "free_y",
             labeller = labeller(capsule = \(x)
               str_c("<span style='color:", PAL$capsule[x], "'>", x, "</span>"))) +
  scale_color_manual(values = PAL$capsule) +
  scale_x_continuous(limits = c(0, 1), breaks = c(0, .5, 1),
                     labels = c("0", "0.5", "1")) +
  labs(
    title = "Given an answer, correctness is a property of the question, not luck",
    subtitle = "Each dot is a question's estimated underlying success probability (posterior median, hierarchical model);\nthe band is 95% uncertainty about that probability — 10 runs cannot pin it exactly even when all 10 agree.",
    x = "estimated probability", y = NULL,
    caption = "Bernoulli GLMMs, question nested in capsule; gpt-5 majority-vote grading. Question-level SD (stage 2): 3.2 log-odds."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank(),
                    legend.position = "none",
                    panel.spacing.x = unit(1.2, "lines"),
                    strip.text.y = element_markdown(face = "bold"))
save_fig(fig2, "fig2_question_rates", 7.5, 4.8)

# ---- fig 3: disagreement follows generation, not family ---------------------

# Three graders: gpt-5 and claude-sonnet-4-5 are different families but the
# same (current) generation; gpt-4o is gpt-5's own family, one generation
# back. The point of the figure: the two current models give identical
# majority verdicts on all 130 answers, while the older family-mate flips
# whole questions — so grader choice is about generation, not vendor.
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
# Dark2 (RColorBrewer) hues chosen to avoid fig2's blue/orange/aqua:
# magenta outer ring, purple middle, mustard center — each ring pair differs
# strongly in hue and lightness so the nesting stays readable
GRADER_COL <- c(`gpt-4o (prev gen)` = "#E7298A",
                `claude-sonnet-4-5` = "#7570B3",
                `gpt-5`             = "#E6AB02")
# sizes spaced so each visible ring is a thick, readable band
GRADER_SIZE <- c(`gpt-4o (prev gen)` = 6.0,
                 `claude-sonnet-4-5` = 3.8,
                 `gpt-5`             = 1.6)

fig3 <- grader_rates |>
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
                     labels = c("0", "0.5", "1")) +
  labs(
    title = "Grader disagreement follows model generation, not model family",
    subtitle = "Fraction of answered runs graded correct per question (majority of 10 grading replicates per grader).\ngpt-5 and claude-sonnet-4-5 — different families, current generation — agree on all 130 answers (nested dots);\ngpt-4o — BixBench's default grader, one generation behind its own family-mate — flips whole questions.",
    x = "fraction graded correct", y = NULL,
    caption = "Same 130 answers under all three graders."
  ) +
  theme_viz + theme(panel.grid.major.y = element_blank())
save_fig(fig3, "fig3_grader_flips", 7.5, 6.6)

message("Wrote figures to results/figures/")
