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
# agent's modal answer — not the key's 3. The 3 only appears when "significant
# enrichment" is read as raw p < 0.05, although the question itself defines
# significance with an adjusted p-value. Either the key used raw p, or it used
# an older KEGG; the stated definition yields 1 today.
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
# adjusted-p definition and under the raw-p reading that reproduces the key.
adj <- setdiff(e_fe$ID[e_fe$p.adjust < 0.05], e_succ$ID[e_succ$p.adjust < 0.05])
raw <- setdiff(e_fe$ID[e_fe$pvalue  < 0.05], e_succ$ID[e_succ$pvalue  < 0.05])
cat("q5 (key 3): padj<0.05 reading =", length(adj), "->", adj, "\n")
cat("            raw p<0.05 reading =", length(raw), "->", raw, "\n")
