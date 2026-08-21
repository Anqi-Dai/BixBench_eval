# What each BixBench capsule is about

One entry per capsule: how many questions it carries, its curated topics, and the
hypothesis the source analysis set out to test. Capsules with a measured cost are
flagged; that cost is per replica at `max_steps: 40` with claude-sonnet-4-5.

Generated from `BixBench.jsonl`. See `results/capsule_families.md` for which
capsules share a source paper, which is currently the only usable cost predictor.


### bix-1  (2 questions)
    topics: Differential Expression Analysis, Network Biology, RNA-seq, Transcriptomics
    hypothesis: Truncating ASXL1 mutations will lead to specific gene expression changes in blood that reflect alterations in hematological processes, such as T cell and neutrophil activ

### bix-2  (2 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: Bloom Syndrome (BSyn) probands and BLM mutation carriers will have a higher mean proportion of low-frequency, somatic CHIP gene variants (VAF < 0.3) compared to control c

### bix-3  (5 questions)
    topics: Differential Expression Analysis, RNA-seq, Transcriptomics
    hypothesis: Antidepressant Paroxetine has negligible effects on gene expression in control (non-depressed) mice

### bix-4  (7 questions)  [MEASURED $7.62/replica]
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Fungi exhibit more clock-like patterns of molecular evolution compared to animals.

### bix-5  (2 questions)
    topics: Differential Expression Analysis, Network Biology, RNA-seq, Transcriptomics
    hypothesis: Truncating ASXL1 mutations that cause Bohring-Opitz syndrome (BOS) will cause specific transcriptional changes that are tissue-specific, such as processes related to cell

### bix-6  (6 questions)
    topics: Functional Genomics
    hypothesis: Immune-relevant pathways will be enriched within the set of genes that, when perturbed, enable cancer cells to evade T cell-mediated cytotoxicity.

### bix-7  (3 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: Bloom Syndrome (BSyn) probands and BLM mutation carriers will have similar levels of germline mutations to controls, but will acquire more DNA mutations, resulting in a h

### bix-8  (6 questions)  [MEASURED $1.35/replica]
    topics: Differential Expression Analysis, Epigenomics, RNA-seq
    hypothesis: mRNA m6A methylation plays a significant role in the development of human bladder cancer

### bix-9  (3 questions)
    topics: Differential Expression Analysis, RNA-seq, Transcriptomics
    hypothesis: Paroxetine induces tissue-specific gene expression changes in depressed mice

### bix-10  (7 questions)
    topics: Other
    hypothesis: Tubercolosis BCG re-vaccination reduces COVID-19 disease severity among healthcare workers

### bix-11  (6 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis
    hypothesis: Fungi have higher treeness values compared to animals.

### bix-12  (5 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Fungi have more parsimony informative sites compared to animals.

### bix-13  (5 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: Knocking out either rhlI or lasI impacts the downstream expression of dozens of genes which may be involved in mediating the observed division of labor.

### bix-14  (3 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: The distribution of variant effects / types of putative somatic CHIP variants in Bloom Syndrome probands and carriers will not differ significantly from that of controls.

### bix-16  (4 questions)
    topics: Functional Genomics, Transcriptomics
    hypothesis: Genes with higher expression levels are more critical for cancer cell survival and exhibit higher essentiality.

### bix-17  (1 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: The increased number of somatic variants in CHIP (clonal haematopoiesis of indeterminate potential) genes found in Bloom syndrome probands and carriers is not an effect o

### bix-18  (5 questions)
    topics: Imaging
    hypothesis: Disrupting genes in either the las or rhl quorum sensing (QS) systems, either the receptors or the synthases, abrogates swarming motility, a form of movement that allows 

### bix-19  (5 questions)
    topics: Imaging, Other
    hypothesis: Significant neuronal damage is induced by OXTR gene knockdown across rodent species

### bix-20  (4 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: The distribution of variant pathogenicity of putative somatic CHIP variants in Bloom Syndrome probands and carriers will not differ significantly from that of controls.

### bix-21  (1 questions)
    topics: Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Animals will have lower signatures of saturation by multiple substitutions than fungi.

### bix-22  (5 questions)
    topics: RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: Gene length positively correlates with expression level across immune cell types in children

### bix-24  (3 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: CBD treatment of CRC cells causes metabolic dysregulation in the cells

### bix-25  (2 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Treeness/RCV values differ between fungal and animal single-copy orthologous genes and correlate with alignment properties.

### bix-26  (3 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: Downstream gene expression of rhlI and lasI mutants is altered in different media suggesting that quorum sensing-mediated division of labor is environment-dependent.

### bix-27  (3 questions)
    topics: Machine Learning and Artificial Intelligence, RNA-seq, Transcriptomics
    hypothesis: Alzheimer’s disease patients can be subtyped by gene expression, suggesting distinct mechanisms and therapeutic targets.

### bix-28  (6 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Long branch scores differ significantly between fungal and animal phylogenies, indicating different evolutionary patterns.

### bix-29  (4 questions)
    topics: Other
    hypothesis: Prior history of severe disease correlates with increased COVID-19 severity among healthcarre workers following BCG re-vaccination

### bix-30  (4 questions)
    topics: Differential Expression Analysis, Transcriptomics
    hypothesis: Serum miRNAs can be used as Myotonic Dystrophy Type 1 Biomarkers

### bix-31  (4 questions)
    topics: Differential Expression Analysis, RNA-seq, Transcriptomics
    hypothesis: Sex-specific differences in gene expression are more pronounced in protein-coding genes within CD4 and CD8 cells

### bix-32  (3 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: Knocking out either lasI, rhlI, or both simultaneously, alters the expression of numerous downstream pathways of diverse functions.


### bix-33  (2 questions)
    topics: Differential Expression Analysis, Single-Cell Analysis
    hypothesis: AAV9 mini-dystrophin treatment leads to a downregulation of anti-inflammatory pathways in peripheral immune cells

### bix-34  (6 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Patristic distances differ between fungal and animal phylogenies, reflecting different evolutionary rates and patterns.

### bix-35  (4 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Evolutionary rates differ significantly between fungal and animal lineages, with fungi showing accelerated evolution.

### bix-36  (4 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: miRNAs exhibit a constant expression profile across immune-related cell types

### bix-37  (4 questions)
    topics: Differential Expression Analysis, Proteomics, RNA-seq
    hypothesis: Proteomics levels of ENO1 are different between tumour and control, in human bladder cancer

### bix-38  (5 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Tree lengths differ significantly between fungal and animal phylogenies, with fungi showing longer tree lengths indicative of greater evolutionary divergence.

### bix-39  (1 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: Bloom Syndrome (BSyn) probands and BLM mutation carriers will have a higher number of low-frequency, somatic CHIP gene variants (VAF < 0.3) compared to control cohorts, g

### bix-41  (4 questions)
    topics: Imaging
    hypothesis: Co-culturing the strains with single-gene knockouts (ΔrhlI and ΔlasI) in the reciprocal QS pathways rhl and las, restores wildtype swarming behavior for the population as

### bix-42  (2 questions)
    topics: Genomics, Integrative Omics, Machine Learning and Artificial Intelligence, Other, Transcriptomics
    hypothesis: Multimodal integration of RNA expression data and DNA methylation data improves the accuracy of colon cancer survival prediction compared to single-modality models.

### bix-43  (5 questions)  [MEASURED $3.22/replica]
    topics: Differential Expression Analysis, RNA-seq, Transcriptomics
    hypothesis: combination treatment of CBD and chemotheraputics of CRC cells enriches for cell cycle regulation and apoptosis processes

### bix-45  (4 questions)
    topics: Genomics, Phylogenetics, Whole Genome Sequencing (WGS)
    hypothesis: Relative Composition Variability (RCV) analysis reveals significant differences in compositional heterogeneity between animal and fungal orthologous genes, with fungi sho

### bix-46  (2 questions)
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: Genes that are downregulated in either ΔrhlI or ΔlasI strains are candidates for receiving complementation from the other strain and are therefore important candidates fo

### bix-47  (2 questions)
    topics: Genomic Variant Analysis, Genomics
    hypothesis: We hypothesize that the gene distribution of putative somatic CHIP variants are not significantly different across individuals with or without mutations in the BLM gene (

### bix-49  (5 questions)
    topics: Differential Expression Analysis, RNA-seq, Transcriptomics
    hypothesis: Truncating ASXL1 mutations that cause Bohring-Opitz syndrome will lead to significant dysregulation of gene expression in blood RNA-seq, with a higher number of different

### bix-51  (7 questions)
    topics: Other
    hypothesis: Patient demographics (age, BMI, gender) significantly influence the likelihood of achieving remission (CR/PR) with camrelizumab in advanced hepatocellular carcinoma

### bix-52  (6 questions)
    topics: Epigenomics
    hypothesis: Age-Related DNA Methylation is Equally Distributed Across Chromosomes

### bix-53  (5 questions)  [MEASURED $2.86/replica]
    topics: Differential Expression Analysis, RNA-seq, Sequence Analysis, Transcriptomics
    hypothesis: UBEM2 KD in macrophages attenuates antioxidant processes in the cells

### bix-54  (7 questions)
    topics: Imaging
    hypothesis: QS gene mutants ΔrhlI and ΔlasI demonstrate division of labor when they are co-cultured at an optimal ratio, leading to improved fitness even when compared with wildtype 

### bix-55  (1 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: BUSCO analysis can identify shared single-copy orthologs across distantly related species.

### bix-56  (1 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Orthologous protein sequences can be successfully extracted and compiled from BUSCO results across multiple species for comparative analysis.

### bix-57  (1 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis
    hypothesis: Multiple sequence alignment can be performed on orthologous protein sequences with measurable gap content reflecting evolutionary insertions and deletions.

### bix-58  (1 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis
    hypothesis: Alignment trimming can improve phylogenetic signal by removing poorly aligned regions while preserving informative sites.

### bix-60  (1 questions)
    topics: Genomics, Phylogenetics and Evolutionary Analysis
    hypothesis: Phylogenetic trees can be assessed for quality using treeness statistics that measure the strength of hierarchical phylogenetic signal.

### bix-61  (6 questions)
    topics: Antimicrobial Resistance, Genomics, SNP Analysis, Whole Genome Sequencing (WGS)
    hypothesis: Multi-drug resistant (MDR) E. coli strains will exhibit higher mutation rates resulting in more SNPs compared to retail meat isolates, and transition mutations will predo
