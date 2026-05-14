# Introduction

PRCGAP (<u>**P**</u>ersonalized <u>**R**</u>eference genome-based <u>**C**</u>ancer <u>**G**</u>enome <u>**A**</u>nalysis <u>**P**</u>ipeline) is a Snakemake workflow for comprehensive cancer genome analysis on a personalized reference genome — a phased de novo assembly of the same individual — using long-read sequencing data (PacBio HiFi and Oxford Nanopore Technologies).

## Overview

- Performs somatic variant calling, copynumber profiling, and DNA mehtylation analysis against a personalized reference genome.
- **Inputs:** a tumor / normal pair of ONT and HiFi reads (BAM or FASTQ.gz), plus the corresponding hap1 / hap2 assembly FASTAs.
- **Outputs:** point mutation, structural variant (SV), copy number, and methylation callsets.

PRCGAP is responsible for variant calling and post-processing on the personalized reference genome. Generating the personalized reference genome and the accompanying annotation files is treated as a separate, upstream step; see [Preparation.md](./Preparation.md) for how those inputs are produced and supplied to PRCGAP.

## Analysis modules

The modules below mirror the Analysis Steps section of `PRCGAP/README.md`:

| Module | Description | Container image |
|--------|-------------|-----------------|
| BAM Refiner | Align tumor / normal reads to the phased de novo assemblies | `bam_refiner` |
| Methylation | Methylation calling for HiFi and  ONT data | `methylation` |
| Copy Number | Copy number profiling | `copynumber` |
| NanomonSV pipeline | parse → get → postprocess → insert classify → connect → HiFi/ONT merge | `nanomonsv`, `nanomonsv_postprocess` |
| Point mutation (ClairS) | Somatic SNV/indel calling and post-processing (realignment / pileup / haplotyping) | `clairs`, `point_mutation_postprocess` |
| Point mutation (DeepSomatic) | Somatic SNV/indel calling and post-processing | `deepsomatic`, `point_mutation_postprocess` |

High-level dependencies between modules:

- `bam_refiner` outputs feed methylation, copynumber, nanomonsv, clairs, and deepsomatic.
- ClairS and DeepSomatic raw calls are passed to `point_mutation_postprocess` for realignment, pileup, and haplotyping.
- Nanomonsv is run per seqtype (HiFi and ONT), and the final step merges the two callsets.

The full DAG and rule-file map are in [Workflow.md](./Workflow.md).

## Table of contents

1. [Introduction](./Introduction.md) — this page
2. [Preparation](./Preparation.md) — preparing the personalized reference and annotation files that PRCGAP consumes
3. [Usage](./Usage.md) — installation, sample sheet, `setup_workflow.py`, and how to run the workflow
4. [Workflow](./Workflow.md) — DAG, inter-module dependencies, rule files, output layout
5. [Example](./Example.md) — end-to-end run on a tumor / normal pair

## Contact

Yoshitaka Sakamoto
yosakam@ncc.go.jp

## Citation
*Pending*

