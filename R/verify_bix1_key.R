# Recompute the bix-1 answer key (same ASXL1 blood data as bix-49).
#
# Both questions ask for enrichGO adjusted p-values after
# clusterProfiler::simplify(cutoff = 0.7). Two findings:
#   q1 — the key (0.0002, 4 dp) reproduces only when the DESeq2 design is
#        ~sex + condition, the same hidden covariate that generates the bix-49
#        key. The plain ~condition design gives 0.0029.
#   q2 — "neutrophil activation" is removed by the simplify() step the
#        question itself mandates, under every design tried. The key's 1.9e-05
#        is a pre-simplify value; the agent reported the pre-simplify value
#        for its own run (1.26e-04, matching ~condition) and noted the removal.
# GO term p-values also depend on the org.Hs.eg.db release, so pre-simplify
# values can only be matched to the order of magnitude.
#
# Run inside the BixBench image:
#   docker run --rm \
#     -v .../CapsuleFolder-33b801bb-9b47-4a0a-9314-05325c82fde7:/data:ro \
#     -v "$PWD/R:/scripts:ro" \
#     futurehouse/bixbench:aviary-notebook-env Rscript /scripts/verify_bix1_key.R

suppressMessages({library(DESeq2); library(readxl); library(clusterProfiler)
                  library(org.Hs.eg.db)})

cnt <- read.table("/data/Issy_ASXL1_blood_featureCounts_GeneTable_final.txt",
                  header = TRUE, row.names = 1, check.names = FALSE)
cd  <- as.data.frame(read_excel("/data/Issy_ASXL1_blood_coldata_gender.xlsx"))
rownames(cd) <- cd$sample
map <- read.csv("/data/gencode.v31.primary_assembly.genes.csv")
map$ens <- sub("\\..*", "", map$gene_id)

common <- intersect(colnames(cnt), cd$sample)
cnt19  <- cnt[, common]
cd19   <- cd[common, ]
cd19$condition <- factor(cd19$condition, levels = c("Control", "ASXL1"))
cd19$sex       <- factor(cd19$sex)

# For each design: DEGs at the question's threshold, enrichGO over the gencode
# universe (q2 names it as the background), then the two target terms before
# and after simplify.
report <- function(label, design, use_padj) {
  dds <- DESeqDataSetFromMatrix(round(as.matrix(cnt19)), cd19, design)
  dds <- suppressMessages(DESeq(dds, quiet = TRUE))
  res <- as.data.frame(lfcShrink(dds, coef = "condition_ASXL1_vs_Control",
                                 type = "apeglm", quiet = TRUE))
  res$symbol <- map$gene_name[match(sub("\\..*", "", rownames(res)), map$ens)]
  keep <- if (use_padj) !is.na(res$padj) & res$padj < 0.05
          else               !is.na(res$pvalue) & res$pvalue < 0.05
  genes    <- unique(na.omit(res$symbol[keep]))
  universe <- unique(na.omit(res$symbol))
  ego  <- enrichGO(gene = genes, universe = universe, OrgDb = org.Hs.eg.db,
                   keyType = "SYMBOL", ont = "BP", pvalueCutoff = 0.05)
  pre  <- as.data.frame(ego)
  post <- as.data.frame(clusterProfiler::simplify(ego, cutoff = 0.7))
  for (term in c("regulation of T cell activation", "neutrophil activation")) {
    p_pre  <- pre$p.adjust[pre$Description == term]
    p_post <- post$p.adjust[post$Description == term]
    cat(sprintf("%s | %-32s pre-simplify: %s | post-simplify: %s\n",
                label, term,
                if (length(p_pre))  format(p_pre,  digits = 4) else "absent",
                if (length(p_post)) format(p_post, digits = 4) else "removed"))
  }
}

# q1 selects DEGs at padj < 0.05; q2 says raw p < 0.05. Both designs are run
# for each so the covariate's effect is visible either way.
report("q1 ~condition      ", ~condition,       TRUE)
report("q1 ~sex + condition", ~sex + condition, TRUE)
report("q2 ~condition      ", ~condition,       FALSE)
report("q2 ~sex + condition", ~sex + condition, FALSE)
