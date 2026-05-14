# Example

This page walks through an end-to-end PRCGAP run on the in-house tumor / normal pair **H2009 (tumor) / BL2009 (normal)**, using a personalized reference genome built from the matched normal.

## Overview

```
   ┌─────────────────────────┐        ┌───────────────────────┐
   │   Personalized          │  ───▶  │       PRCGAP          │
   │   reference + annots    │        │ (BAM refine, SV,      │
   │ (built per Preparation) │        │  CNV, methylation,    │
   │                         │        │  point mutations)     │
   └─────────────────────────┘        └───────────────────────┘
         produces                            consumes
         - hap1 / hap2 FASTA                 - assembly_hap1 / hap2
         - dna-brnn BED (per hap)            - hap{1,2}_satellite
         - simple_repeats BED                - simple_repeat
         - LINE1 BED                         - line1_bed
         - liftoff GTF                       - gtf_file
```

## Step 1 — Prepare the personalized reference

Follow [Preparation.md](./Preparation.md) to produce, for sample `2009` (the matched normal of H2009), the per-haplotype assemblies and annotation files. After running those steps, you should have a layout such as:

```
/data/2009/
├── assembly/
│   ├── 2009.hap1.filt.fa
│   └── 2009.hap2.filt.fa
└── annotation/
    ├── 2009.hap1_dna-brnn.bed.gz
    ├── 2009.hap2_dna-brnn.bed.gz
    ├── 2009.simple_repeats.bed.gz
    ├── 2009.LINE1.bed.gz
    └── 2009.liftoff.gtf.gz
```

Mapping to PRCGAP inputs:

| File | PRCGAP role |
|------|-------------|
| `/data/2009/assembly/2009.hap1.filt.fa` | `samplesheet.tsv` `assembly_hap1` |
| `/data/2009/assembly/2009.hap2.filt.fa` | `samplesheet.tsv` `assembly_hap2` |
| `/data/2009/annotation/2009.hap1_dna-brnn.bed.gz` | `--hap1-satellite` |
| `/data/2009/annotation/2009.hap2_dna-brnn.bed.gz` | `--hap2-satellite` |
| `/data/2009/annotation/2009.simple_repeats.bed.gz` | `--simple-repeat` |
| `/data/2009/annotation/2009.LINE1.bed.gz` | `--line1-bed` |
| `/data/2009/annotation/2009.liftoff.gtf.gz` | `--gtf-file` |

## In-house resource paths

When running on NCC infrastructure, the auxiliary resources commonly required are stored at:

| Resource | Typical location |
|----------|------------------|
| GRCh38 reference FASTA | `/<shared>/references/GRCh38/...` |
| Ensembl GTF (used in step 3 of Preparation.md) | `/<shared>/references/Ensembl/...` |
| Singularity images for PRCGAP | `/<shared>/singularity/prcgap/*.sif` |
| DNA-NN model (`attcc-alpha.knm`) | `/<shared>/resources/dna-nn/attcc-alpha.knm` |

> Replace `<shared>` with the actual storage prefix used by your group. Confirm exact paths with the group lead before pointing PRCGAP at them.

## Step 2 — Author the PRCGAP sample sheet

Both rows of the pair point to the **same** assembly FASTAs (those built in step 1):

```tsv
sample  type    ont                     hifi                    assembly_hap1                       assembly_hap2
H2009   tumor   /data/H2009_ont.bam     /data/H2009_hifi.bam    /data/2009/assembly/2009.hap1.filt.fa  /data/2009/assembly/2009.hap2.filt.fa
BL2009  normal  /data/BL2009_ont.bam    /data/BL2009_hifi.bam   /data/2009/assembly/2009.hap1.filt.fa  /data/2009/assembly/2009.hap2.filt.fa
```

Save as `samples.tsv`.

## Step 3 — Generate `config.yaml`

```bash
python3 PRCGAP/setup_workflow.py \
    --samplesheet $(pwd)/samples.tsv \
    --reference /shared/references/GRCh38/GRCh38.fa \
    --bam-refiner-image /shared/singularity/prcgap/bam_refiner.sif \
    --methylation-image /shared/singularity/prcgap/methylation.sif \
    --copynumber-image /shared/singularity/prcgap/copynumber.sif \
    --nanomonsv-image /shared/singularity/prcgap/nanomonsv.sif \
    --nanomonsv-postprocess-image /shared/singularity/prcgap/nanomonsv_postprocess.sif \
    --clairs-image /shared/singularity/prcgap/clairs.sif \
    --deepsomatic-image /shared/singularity/prcgap/deepsomatic.sif \
    --point-mutation-postprocess-image /shared/singularity/prcgap/point_mutation_postprocess.sif \
    --full-pipeline \
    --hap1-satellite /data/2009/annotation/2009.hap1_dna-brnn.bed.gz \
    --hap2-satellite /data/2009/annotation/2009.hap2_dna-brnn.bed.gz \
    --simple-repeat  /data/2009/annotation/2009.simple_repeats.bed.gz \
    --line1-bed      /data/2009/annotation/2009.LINE1.bed.gz \
    --gtf-file       /data/2009/annotation/2009.liftoff.gtf.gz \
    --sex female \
    --output-dir $(pwd)/results \
    --output $(pwd)/config.yaml
```

## Step 4 — Run the workflow

### Local

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile $(pwd)/config.yaml \
    --directory $(pwd)/results \
    --sdm apptainer \
    --apptainer-args "-B /data -B /shared" \
    --cores 16 \
    --resources mem_mb=128000
```

### Cluster (UGE example)

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile $(pwd)/config.yaml \
    --directory $(pwd)/results \
    --profile /path/to/PRCGAP/profile/uge
```

A SLURM run is identical with `--profile /path/to/PRCGAP/profile/slurm`. Tune `singularity-args`, `jobs`, and `latency-wait` in the profile's `config.yaml` for your cluster (see [Usage.md](./Usage.md)).

## Step 5 — Expected outputs and sanity checks

For the H2009 / BL2009 pair, the run directory should contain:

| Module | Path | Sanity check |
|--------|------|--------------|
| BAM Refiner | `results/bam_refiner/H2009/hifi/`, `.../ont/`, and same for `BL2009` | Refined BAM + index exists; `samtools quickcheck` passes |
| Methylation | `results/methylation/H2009/hifi/`, `.../ont/` (and `BL2009`) | Per-CpG / per-position methylation tables non-empty |
| Copy Number | `results/copynumber/H2009/` | Copy number segments file present and non-empty |
| NanoMonSV per seqtype | `results/nanomonsv/hifi/`, `results/nanomonsv/ont/` | Parsed and post-processed SV tables exist |
| NanoMonSV merged | `results/nanomonsv/H2009.*.merged.txt` | Merged HiFi+ONT SV table written |
| ClairS | `results/clairs/H2009/` | Raw ClairS VCF present |
| ClairS post | `results/clairs_post/H2009/` | Realigned / pileup / haplotyped outputs present |
| DeepSomatic | `results/deepsomatic/H2009/` | Raw DeepSomatic VCF present |
| DeepSomatic post | `results/deepsomatic_post/H2009/` | Post-processed outputs present |
| Logs | `results/logs/` | Per-rule logs available for debugging |

A quick way to confirm a run completed successfully is:

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile $(pwd)/config.yaml \
    --directory $(pwd)/results \
    --summary
```

If anything is reported as `incomplete` or `missing`, inspect the corresponding log under `results/logs/`.

## Related pages

- [Preparation.md](./Preparation.md) — Producing the personalized reference and annotation files
- [Usage.md](./Usage.md) — Sample sheet, `setup_workflow.py`, run options
- [Workflow.md](./Workflow.md) — DAG, rule files, output layout
