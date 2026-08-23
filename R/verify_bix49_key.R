# Recompute the bix-49 answer key and the agent's answers from the raw counts.
#
# The capsule ships a 21-sample count matrix and a 19-sample coldata file, and
# the review initially blamed the answer gap on that mismatch. Running the
# candidate analyses shows otherwise: the agent's numbers are the exact DESeq2
# output for the 19 matched samples with design ~condition, and the answer key
# is the exact output for the same 19 samples with design ~sex + condition.
# The disagreement is a hidden covariate, not sample inclusion.
#
# Base R rather than tidyverse because this runs inside the benchmark's own
# Docker image, which is pinned to the packages the agent had.
#
# Run inside the BixBench image with the capsule mounted at /data:
#   docker run --rm \
#     -v .../CapsuleFolder-4ef3fcd8-1c35-466f-9d93-49b92f4ea760:/data:ro \
#     -v "$PWD/R:/scripts:ro" \
#     futurehouse/bixbench:aviary-notebook-env Rscript /scripts/verify_bix49_key.R

suppressMessages({library(DESeq2); library(readxl); library(apeglm)})

# The count table is whitespace-delimited featureCounts output; the coldata
# spreadsheet covers only 19 of its 21 samples (MGD1640B and MGD1641B have no
# condition label anywhere in the capsule).
cnt <- read.table("/data/Issy_ASXL1_blood_featureCounts_GeneTable_final.txt",
                  header = TRUE, row.names = 1, check.names = FALSE)
cd  <- as.data.frame(read_excel("/data/Issy_ASXL1_blood_coldata_gender.xlsx"))
rownames(cd) <- cd$sample
cat("counts:", ncol(cnt), "samples; coldata:", nrow(cd), "samples;",
    "unmatched:", setdiff(colnames(cnt), cd$sample), "\n\n")

# GRIK5 has to be found by symbol, so map Ensembl ids through the gencode v31
# table the capsule provides.
map <- read.csv("/data/gencode.v31.primary_assembly.genes.csv")
map$ens <- sub("\\..*", "", map$gene_id)

common <- intersect(colnames(cnt), cd$sample)
cnt19  <- cnt[, common]
cd19   <- cd[common, ]
cd19$condition <- factor(cd19$condition, levels = c("Control", "ASXL1"))
cd19$sex       <- factor(cd19$sex)

# One DESeq2 run per candidate design, reporting every quantity the five
# questions ask about. The max-LFC line reports both significance readings of
# q1 ("statistically significant (p<0.05)"): raw p, which is what the wording
# says, and padj, which is what the key uses.
report <- function(label, design) {
  dds <- DESeqDataSetFromMatrix(round(as.matrix(cnt19)), cd19, design)
  dds <- suppressMessages(DESeq(dds, quiet = TRUE))
  res <- lfcShrink(dds, coef = "condition_ASXL1_vs_Control",
                   type = "apeglm", quiet = TRUE)
  sym <- map$gene_name[match(sub("\\..*", "", rownames(res)), map$ens)]
  sig    <- !is.na(res$padj) & res$padj < 0.05
  up     <- sig & res$log2FoldChange > 0
  up_raw <- !is.na(res$pvalue) & res$pvalue < 0.05 & res$log2FoldChange > 0
  gk <- which(sym == "GRIK5")[1]
  cat(sprintf(paste0(
    "%s\n  q4 total padj<.05 = %d | q3 up = %d | down = %d\n",
    "  q1 max LFC: padj-based = %.4f, raw-p-based = %.4f\n",
    "  q2 GRIK5 padj = %.4e | q5 GRIK5 LFC = %.4f\n\n"),
    label, sum(sig), sum(up), sum(sig) - sum(up),
    max(res$log2FoldChange[up]), max(res$log2FoldChange[up_raw]),
    res$padj[gk], res$log2FoldChange[gk]))
}

# ~condition reproduces the agent (1754 / 1096 / 5.15 / 8.76e-25 / 3.87);
# ~sex + condition reproduces the answer key (2118 / 1166 / 4.80 / 7.04e-26 /
# 3.83). No question mentions adjusting for sex.
report("design ~condition        (matches the agent)", ~condition)
report("design ~sex + condition  (matches the answer key)", ~sex + condition)
