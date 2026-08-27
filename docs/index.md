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
      text: Quick start
      link: /QuickStart
    - theme: alt
      text: Introduction
      link: /Introduction
    - theme: alt
      text: View on GitHub
      link: https://github.com/yos-sk/PRCGAP

features:
  - title: Personalized reference
    details: Calls variants against a sample-specific phased de novo assembly, which can identify somatic mutations in centromeric, telomeric, and other highly repetitive regions that standard reference-based pipelines cannot resolve.
  - title: Long-read native
    details: Built around PacBio HiFi and Oxford Nanopore reads, together or on their own — HiFi-only and ONT-only pairs are first-class. Methylation via pb-CpG-tools / modkit, SVs via Nanomonsv, point mutations via DeepSomatic and ClairS.
  - title: Reads, assembly, references
    details: PRCGAP builds its own per-assembly annotation — gene models, satellites, LINE-1, tandem repeats, liftover chains — so a run needs nothing more than the reads, the assembly, and a one-time reference download. Deeper annotation is optional.
  - title: Reproducible by design
    details: Every step runs inside Singularity / Apptainer images pulled from Docker Hub. Local, UGE/SGE, and SLURM execution are all driven by one generated runner script.
---
