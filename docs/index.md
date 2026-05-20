---
layout: home

hero:
  name: PRCGAP
  text: Personalized Reference genome-based Cancer Genome Analysis Pipeline 
  tagline: |
    Snakemake workflow for comprehensive tumor/normal cancer genome analysis
    using long-read sequencing (PacBio HiFi & Oxford Nanopore Technologies) on phased de
    novo assemblies of the normal samples.
  actions:
    - theme: brand
      text: Get Started
      link: /Introduction
    - theme: alt
      text: Setup
      link: /Usage
    - theme: alt
      text: View on GitHub
      link: https://github.com/yos-sk/PRCGAP

features:
  - title: Personalized reference
    details: Calls variants against a sample-specific phased de novo assembly, which can identify somatic mutations in centromeric, telomeric, and other highly repetitive regions that standard reference-based pipelines cannot resolve.
  - title: Long-read native
    details: Built around PacBio HiFi and Oxford Nanopore reads. Methylation via pb-CpG-tools / modkit, SVs via Nanomonsv, point mutations via ClairS and DeepSomatic.
  - title: Reproducible by design
    details: Every step runs inside Singularity / Apptainer images. Local, UGE, and SLURM execution profiles are bundled.
---
