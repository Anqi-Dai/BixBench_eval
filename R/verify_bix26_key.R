# Recompute the bix-26 answer key from the capsule's DESeq2 results.
#
# The capsule ships two gene-level DESeqResults objects for P. aeruginosa PA14
# (iron-depleted glucose vs replete, and succinate/"innate" vs replete). All
# three questions filter DEGs at |log2FC| > 1.5 & padj < 0.05 and run KEGG
# over-representation via clusterProfiler against the live KEGG REST service,
# so every answer is pinned to whatever KEGG contains on the day it runs.
#
# Against KEGG as of 2026-08-23 this reproduces the q3 key (11) and the q4 key
# (5) exactly, which validates the pipeline reading. q5 then gives 1 — the
# agent's modal answer — not the key's 3.
#
# The key's 3 is explained by the author's own notebook (on the Hugging Face
# hub inside the capsule zip; the harness strips it from what the agent sees):
# the author filters DEGs by fold change only — the padj < 0.05 threshold the
# question states is never applied — runs enrichment separately for up- and
# downregulated genes, and never computes the set difference in code (the
# notebook ends at a dotplot, so the key was read off the plot). The second
# block below reruns that exact pipeline; it reproduces all three keys today,
# so KEGG drift is not in play for this capsule.
#
# Run inside the BixBench image (needs network access for KEGG):
#   docker run --rm \
#     -v .../CapsuleFolder-0923d260-fe1b-4fb4-4398-79edf546e584:/data:ro \
#     -v "$PWD/R:/scripts:ro" \
#     futurehouse/bixbench:aviary-notebook-env Rscript /scripts/verify_bix26_key.R

suppressMessages(library(clusterProfiler))

fe   <- as.data.frame(readRDS("/data/res_GluFevsGluFePlus.rds"))    # iron-depleted
succ <- as.data.frame(readRDS("/data/res_SuccvsGluFePlus.rds"))     # innate media

# DEG lists under the thresholds every question states.
pick <- function(res, dir = c("both", "up", "down")) {
  dir <- match.arg(dir)
  ok <- !is.na(res$padj) & res$padj < 0.05
  ok <- ok & switch(dir,
                    up   = res$log2FoldChange >  1.5,
                    down = res$log2FoldChange < -1.5,
                    both = abs(res$log2FoldChange) > 1.5)
  rownames(res)[ok]
}

# pvalueCutoff = 1 keeps the full table so both significance readings can be
# taken from one enrichment run. "pau" is KEGG's code for strain UCBPP-PA14.
kegg <- function(genes) {
  as.data.frame(enrichKEGG(gene = genes, organism = "pau",
                           pvalueCutoff = 1, qvalueCutoff = 1))
}

e_fe   <- kegg(pick(fe))
e_succ <- kegg(pick(succ))

# q3 — genes contributing to 'ABC transporters' among upregulated FeMinus DEGs.
e_up <- kegg(pick(fe, "up"))
abc <- e_up[grepl("ABC transporters", e_up$Description) & e_up$p.adjust < 0.05, ]
cat("q3 (key 11): ABC transporters Count =", abc$Count, "\n")

# q4 — pathways enriched in the downregulated genes of both conditions.
dn_common <- intersect(kegg(pick(fe, "down"))$ID[kegg(pick(fe, "down"))$p.adjust < 0.05],
                       kegg(pick(succ, "down"))$ID[kegg(pick(succ, "down"))$p.adjust < 0.05])
cat("q4 (key 5): common down-pathways =", length(dn_common), "\n")

# q5 — enriched under iron depletion but not innate media, under the stated
# adjusted-p definition. This is the answer the question's own text implies.
adj <- setdiff(e_fe$ID[e_fe$p.adjust < 0.05], e_succ$ID[e_succ$p.adjust < 0.05])
cat("q5 (key 3): stated-thresholds reading =", length(adj), "->", adj, "\n\n")

# --- The author's actual pipeline, transcribed from the capsule notebook ---
# Gene filter is fold change only (no padj), enrichment runs per direction
# with qvalueCutoff = 0.05, and per-condition pathway sets are the union of
# the up and down results. Reproduces all three keys, including q5 = 3.
k_auth <- function(genes) {
  as.data.frame(enrichKEGG(gene = genes, organism = "pau",
                           pvalueCutoff = 0.05, qvalueCutoff = 0.05))
}
fe_up <- k_auth(rownames(fe)[fe$log2FoldChange >  1.5])
fe_dn <- k_auth(rownames(fe)[fe$log2FoldChange < -1.5])
su_up <- k_auth(rownames(succ)[succ$log2FoldChange >  1.5])
su_dn <- k_auth(rownames(succ)[succ$log2FoldChange < -1.5])
abc_a <- fe_up[grepl("ABC transporters", fe_up$Description), ]
cat("author pipeline  q3:", abc_a$Count,
    "| q4:", length(intersect(fe_dn$ID, su_dn$ID)),
    "| q5:", length(setdiff(union(fe_up$ID, fe_dn$ID), union(su_up$ID, su_dn$ID))), "\n")
