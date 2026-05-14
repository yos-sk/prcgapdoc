---
layout: home

hero:
  name: PRCGAP
  text: Cancer genome analysis on a personalized reference
  tagline: |
    Snakemake workflow for comprehensive tumor/normal cancer genome analysis
    using long-read sequencing (PacBio HiFi & Oxford Nanopore Technologies) on phased de
    novo assemblies of the same individual.
  actions:
    - theme: brand
      text: Get Started
      link: /Introduction
    - theme: alt
      text: Setup
      link: /Usage
    - theme: alt
      text: View on GitHub
      link: https://github.com/

features:
  - title: Personalized reference
    details: Calls variants against a sample-specific phased de novo assembly produced by the upstream assembly_workflow, reducing reference bias in structurally complex regions.
  - title: Long-read native
    details: Built around PacBio HiFi and Oxford Nanopore reads. Methylation via pb-CpG-tools / modkit, SVs via NanoMonSV, point mutations via ClairS and DeepSomatic.
  - title: Reproducible by design
    details: Every step runs inside Singularity / Apptainer images. Local, UGE, and SLURM execution profiles are bundled.
---
