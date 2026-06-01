# Introduction

PRCGAP (<u>**P**</u>ersonalized <u>**R**</u>eference genome-based <u>**C**</u>ancer <u>**G**</u>enome <u>**A**</u>nalysis <u>**P**</u>ipeline) is a Snakemake workflow for comprehensive cancer genome analysis on a personalized reference genome — a phased de novo assembly of the same individual — using long-read sequencing data (PacBio HiFi and Oxford Nanopore Technologies).

## Overview

- Performs somatic variant calling (point mutations and structural variants), copynumber profiling, and DNA mehtylation analysis against a personalized reference genome.
- **Inputs:** a tumor / normal pair of ONT and HiFi reads (BAM or FASTQ.gz), plus the corresponding hap1 / hap2 assembly FASTAs.
- **Outputs:** point mutation, structural variant (SV), copy number, and methylation callsets, each annotated against gene / repeat / centromere / segdup / gnomAD references and lifted to GRCh38 / CHM13 for variants.

PRCGAP is responsible for variant calling, post-processing, and annotation on the personalized reference genome. Generating the personalized reference genome and the accompanying annotation files is treated as a separate, upstream step; see [Preparation.md](./Preparation.md) for how those inputs are produced and supplied to PRCGAP.

## Analysis modules

The modules below mirror the Analysis Steps section of `PRCGAP/README.md`:

| Module | Description | Container image |
|--------|-------------|-----------------|
| BAM_refiner | Align tumor / normal reads to the phased de novo assemblies | `bam_refiner` |
| Methylation | Methylation calling for HiFi and  ONT data | `methylation` |
| Copynumber | Copy-number profiling | `copynumber` |
| Nanomonsv pipeline | parse → get → postprocess → insert classify → connect → HiFi/ONT merge | `nanomonsv`, `nanomonsv_postprocess` |
| Point mutation (ClairS) | Somatic SNV/indel calling and post-processing (realignment / pileup / haplotyping) | `clairs`, `point_mutation_postprocess` |
| Point mutation (DeepSomatic) | Somatic SNV/indel calling and post-processing | `deepsomatic`, `point_mutation_postprocess` |
| SV annotation | Per-tumor / per-seqtype SV annotation (gene / RepeatMasker / centromere / segdup / kmer / liftover to GRCh38+CHM13 / gnomAD / misassembly) + SV type reclassification | `annotation` |
| SNV / INDEL annotation | Per-tumor / per-tool SNV+INDEL annotation (lifted coords / gene / RepeatMasker / centromere / segdup / misassembly / cross-tool check / gnomAD) | `annotation` |

High-level dependencies between modules:

- `bam_refiner` outputs feed methylation, copynumber, nanomonsv, clairs, and deepsomatic.
- ClairS and DeepSomatic raw calls are passed to `point_mutation_postprocess` for realignment, pileup, and haplotyping.
- Nanomonsv is run per seqtype (HiFi and ONT), and the final step merges the two callsets.
- The post-processed NanomonSV / ClairS / DeepSomatic callsets feed the annotation modules; SV annotation reclassification additionally consumes the copynumber per-haplotype reference tables.
- Annotation resources (chain files, gene/repeat/centromere/segdup BEDs, gnomAD) are all optional — missing inputs silently skip the corresponding columns rather than failing the DAG.

## Table of contents

1. [Introduction](./Introduction.md) — this page
2. [Preparation](./Preparation.md) — preparing the personalized reference and annotation files that PRCGAP consumes
3. [Usage](./Usage.md) — installation, sample sheet, `setup_workflow.py`, and how to run the workflow
4. [Workflow](./Workflow.md) — DAG, inter-module dependencies, rule files, output layout
5. [Example](./Example.md) — end-to-end run on a tumor / normal pair

## Contact

Yoshitaka Sakamoto
yosakam2@ncc.go.jp

## Citation

Sakamoto Y, Ochi Y, Kogure Y, Kato S, Sato-Otsubo A, Sugawa M, Tanaka Y, Tsujimura T, Mikami T, Nagae G, Chiba K, Okada A, Ito Y, Suzuki H, Aburatani H, Koga Y, Kato I, Takita J, Mano H, Ogawa S, Kataoka K, Kato M, Shiraishi Y. Personalized reference genome-based pipeline reveals comprehensive haplotype-resolved views of cancer genomes. *bioRxiv*. 2026. doi: [10.64898/2026.05.28.728591](https://doi.org/10.64898/2026.05.28.728591)

