# Introduction

PRCGAP (<u>**P**</u>ersonalized <u>**R**</u>eference genome-based <u>**C**</u>ancer <u>**G**</u>enome <u>**A**</u>nalysis <u>**P**</u>ipeline) is a Snakemake workflow for comprehensive cancer genome analysis on a personalized reference genome — a phased de novo assembly of the same individual — using long-read sequencing data (PacBio HiFi and Oxford Nanopore Technologies).

## Overview

- Performs somatic variant calling (point mutations and structural variants), copy-number profiling, and DNA methylation analysis against a personalized reference genome.
- **Inputs:** a tumor / normal pair of long reads — **HiFi, ONT, or both** (bam or fastq.gz) — plus the corresponding hap1 / hap2 assembly FASTAs and a one-time set of public references.
- **Self-contained annotation:** PRCGAP builds the per-assembly annotation it needs (gene models, centromeric satellites, LINE-1, tandem repeats, and liftover chains) from the assembly itself, so a run does not depend on any upstream annotation pipeline.
- **Outputs:** point mutation, structural variant (SV), copy number, and methylation callsets, each annotated against gene / repeat / centromere / segdup / gnomAD references and lifted to GRCh38 / CHM13 for variants.

![PRCGAP pipeline overview](./plot/pipeline.png)

## Getting started

The shortest path is [Quick start](./QuickStart.md): clone, pull the container images, fetch the references once, then hand `setup_workflow.py` your reads, your assembly, and the references. Nothing else is required.

Two things you may want beyond that:

- **The assembly itself.** PRCGAP does not assemble; generate the phased haplotype FASTAs with Hifiasm or Verkko — see [Preparation §1](./Preparation.md#_1-de-novo-assembly-required).
- **Deeper annotation** — RepeatMasker, segmental duplications, cenSat satellite subtypes, and per-haplotype misassembly tracks. These add columns to the SV and SNV/INDEL tables and are entirely optional; the companion [assembly_workflow](https://github.com/yos-sk/assembly_workflow) pipeline produces them. See [Preparation §3](./Preparation.md#_3-optional-deeper-annotation).

## Analysis modules

| Module | Description | Container image |
|--------|-------------|-----------------|
| Assembly annotation | Gene models (liftoff), centromeric satellites (dna-brnn), LINE-1, tandem repeats, and assembly → GRCh38 / CHM13 chain files, built from the assembly | `liftoff`, `dna_nn`, `chain_files`, `nanomonsv` |
| Bam_refiner | Align tumor / normal reads to the phased de novo assemblies | `bam_refiner` |
| Methylation | Methylation calling for HiFi (pb-CpG-tools) and ONT (modkit) data | `methylation` |
| Copynumber | Per-haplotype copy-number profiling, ploidy estimation, and plotting | `copynumber` |
| Nanomonsv pipeline | parse → get → postprocess → insert classify (+ optional connect / HiFi-ONT merge) | `nanomonsv`, `nanomonsv_postprocess` |
| Point mutation (DeepSomatic) | Somatic SNV/indel calling and post-processing — the default caller | `deepsomatic`, `point_mutation_postprocess` |
| Point mutation (ClairS) | Somatic SNV/indel calling and post-processing (realignment / pileup / haplotyping) | `clairs`, `point_mutation_postprocess` |
| SV annotation | Per-tumor / per-seqtype SV annotation (gene / RepeatMasker / centromere / segdup / kmer / liftover to GRCh38+CHM13 / gnomAD / misassembly) + SV type reclassification | `annotation` |
| SNV / INDEL annotation | Per-tumor / per-tool / per-seqtype SNV+INDEL annotation (lifted coords / gene / RepeatMasker / centromere / segdup / misassembly / cross-tool check / gnomAD) | `annotation` |

High-level dependencies between modules:

- Assembly annotation depends only on the assembly pair, so a tumor and its normal annotate once and share the result.
- `bam_refiner` outputs feed methylation, copynumber, nanomonsv, and the point-mutation callers.
- Raw caller output is passed to `point_mutation_postprocess` for realignment, pileup, and haplotyping.
- Nanomonsv runs independently per sequencing type; an optional final step merges HiFi and ONT.
- The post-processed NanomonSV / DeepSomatic / ClairS callsets feed the annotation modules; SV reclassification additionally consumes the copynumber per-haplotype reference tables.
- Every imported annotation resource is optional — a missing input skips the corresponding column rather than failing the DAG.

## Sequencing types

A sample may carry HiFi, ONT, or both. Per-sample steps run for every sequencing type that sample has; tumor / normal steps run for every type present in **both** the tumor and its paired normal. Point mutations default to a single type (HiFi when both are present) and copy number always uses one. See [Usage → Sequencing types](./Usage.md#sequencing-types-hifi-only-ont-only-and-both).

## Table of contents

1. [Introduction](./Introduction.md) — this page
2. [Quick start](./QuickStart.md) — the shortest path from a clone to a finished run
3. [Usage](./Usage.md) — installation, sample sheet, cluster profiles, bind mounts
4. [Options](./Options.md) — every `setup_workflow.py` flag and `config.yaml` key
5. [Preparation](./Preparation.md) — the de novo assembly, and the optional deeper annotation
6. [Workflow](./Workflow.md) — modules, rule files, output layout
7. [Example](./Example.md) — an end-to-end HG008 chr20 run, with the files it produces

## Contact

Yoshitaka Sakamoto
yosakam2@ncc.go.jp

## Citation

Sakamoto Y, Ochi Y, Kogure Y, Kato S, Sato-Otsubo A, Sugawa M, Tanaka Y, Tsujimura T, Mikami T, Nagae G, Chiba K, Okada A, Ito Y, Suzuki H, Aburatani H, Koga Y, Kato I, Takita J, Mano H, Ogawa S, Kataoka K, Kato M, Shiraishi Y. Personalized reference genome-based pipeline reveals comprehensive haplotype-resolved views of cancer genomes. *bioRxiv*. 2026. doi: [10.64898/2026.05.28.728591](https://doi.org/10.64898/2026.05.28.728591)
