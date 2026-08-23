# Recompute bix-43-q3: DEG count for the CBD/cisplatin combination vs DMSO at
# padj < 0.05, |log2FC| > 0.5, baseMean > 10. Key: 677. Agent (one truncated
# pilot run): 525.
#
# The two-group DESeq2 with plain results() gives exactly 525, so the agent's
# answer is the deterministic output of the most literal pipeline. None of the
# defensible variants tried here (apeglm shrinkage, full 30-sample model with
# a contrast, the serum-starved pair) produces 677, so the key's provenance
# remains unidentified.
#
# Run inside the BixBench image:
#   docker run --rm \
#     -v .../CapsuleFolder-15ff11e5-2db1-45b6-b3a3-46bc2a74b821:/data:ro \
#     -v "$PWD/R:/scripts:ro" \
#     futurehouse/bixbench:aviary-notebook-env Rscript /scripts/verify_bix43_key.R

suppressMessages(library(DESeq2))

cnt <- read.csv("/data/counts_raw_unfiltered.csv", row.names = 1, check.names = FALSE)
lay <- read.csv("/data/sample_layout.csv")
lay$SampleID <- gsub("-", "_", lay$SampleID)  # counts name samples 1_1, layout 1-1
rownames(lay) <- lay$SampleID

count_degs <- function(res, label) {
  ok <- !is.na(res$padj) & res$padj < 0.05 &
        abs(res$log2FoldChange) > 0.5 & res$baseMean > 10
  cat(sprintf("%-50s %d\n", label, sum(ok)))
}

two_group <- function(groups, ref) {
  sub <- lay[lay$Group %in% groups, ]
  cd  <- data.frame(row.names = sub$SampleID,
                    condition = relevel(factor(sub$Group), ref = ref))
  suppressMessages(DESeq(DESeqDataSetFromMatrix(
    as.matrix(cnt[, rownames(cd)]), cd, ~condition), quiet = TRUE))
}

# The literal comparison the question names: combination treatment vs DMSO.
dds <- two_group(c("Cisplatin_IC50_CBD_IC50", "DMSO"), "DMSO")
count_degs(results(dds), "two-group combo vs DMSO, results()  [agent: 525]")
count_degs(as.data.frame(lfcShrink(dds, coef = 2, type = "apeglm", quiet = TRUE)),
           "two-group combo vs DMSO, apeglm")

# Full model over all ten groups with an explicit contrast.
cd_all  <- data.frame(row.names = lay$SampleID, condition = factor(lay$Group))
dds_all <- suppressMessages(DESeq(DESeqDataSetFromMatrix(
  as.matrix(cnt[, rownames(cd_all)]), cd_all, ~condition), quiet = TRUE))
count_degs(results(dds_all, contrast = c("condition", "Cisplatin_IC50_CBD_IC50", "DMSO")),
           "full model, contrast combo vs DMSO")

# The serum-starved counterparts, in case the key compared those.
count_degs(results(two_group(c("Cisplatin_IC50_CBD_IC50_Serum_starvation_16h",
                               "DMSO_Serum_starvation"), "DMSO_Serum_starvation")),
           "two-group serum-starved pair, results()")
