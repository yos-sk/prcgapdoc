# Usage

This page covers how to install PRCGAP, author a sample sheet, generate `config.yaml`, and run the workflow locally or on a cluster. It assumes that the personalized reference genome and annotation files described in [Preparation.md](./Preparation.md) are already available.

## Installation

### Prerequisites

- [Snakemake](https://snakemake.readthedocs.io/) 7.x (currently tested with 7.32.4)
- [Apptainer / Singularity](https://apptainer.org/)
- A working build of each PRCGAP container image (see below)

### Building Singularity images

PRCGAP runs every analysis step inside a Singularity image. Dockerfiles for each image live under `PRCGAP/Dockerfile/<tool>/`. The general flow is to build the Docker image first, then convert to Singularity:

```bash
# Build the Docker image
docker build -t prcgap/bam_refiner:v0.3.6 PRCGAP/Dockerfile/bam_refiner/

# Convert to a Singularity image
singularity pull bam_refiner.sif docker://yosakam2/bam_refiner:v0.3.6
```

Repeat for each module. The required images, one per module, are:

| Image | Used by |
|-------|---------|
| `bam_refiner.sif` | BAM Refiner |
| `methylation.sif` | Methylation (HiFi & ONT) |
| `copynumber.sif` | Copy Number |
| `nanomonsv.sif` | NanoMonSV parse / get / insert classify |
| `nanomonsv_postprocess.sif` | NanoMonSV postprocess / connect / merge |
| `clairs.sif` | ClairS |
| `deepsomatic.sif` | DeepSomatic |
| `point_mutation_postprocess.sif` | ClairS / DeepSomatic post-processing (realignment, pileup, haplotyping) |

> Some Dockerfiles contain `TODO` markers for tool-specific install steps that depend on tool versions or licenses. Review each Dockerfile before building.

## Sample sheet

PRCGAP reads samples from a TSV file with one row per sample (tumor and normal are separate rows that share assembly paths).

Required columns:

| Column | Description |
|--------|-------------|
| `sample` | Unique sample identifier |
| `type` | `tumor` or `normal` |
| `ont` | Path(s) to ONT data (BAM or FASTQ.gz). **Multiple files are supported** — list them as a single comma-separated value in this column (no spaces). |
| `hifi` | Path(s) to HiFi data (BAM or FASTQ.gz). **Multiple files are supported** — list them as a single comma-separated value in this column (no spaces). |
| `assembly_hap1` | Path to haplotype 1 de novo assembly (FASTA) — same path for tumor & normal of a pair. |
| `assembly_hap2` | Path to haplotype 2 de novo assembly (FASTA) — same path for tumor & normal of a pair. |

Example (`samples.tsv`):

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
H2009	tumor	/data/H2009_ont.bam	/data/H2009_hifi.bam	/data/2009.hap1.filt.fa	/data/2009.hap2.filt.fa
BL2009	normal	/data/BL2009_ont.bam	/data/BL2009_hifi.bam	/data/2009.hap1.filt.fa	/data/2009.hap2.filt.fa
```

### Multiple input files per sample

The `ont` and `hifi` columns each accept **one or more file paths in a single TSV cell**. When a sample has been sequenced across multiple runs (or split into multiple BAM/FASTQ files for any other reason), list every path joined by commas — **no whitespace around the commas, no quoting, and the entire list stays in one column**.

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
H2009	tumor	/data/H2009_ont.run1.bam,/data/H2009_ont.run2.bam	/data/H2009_hifi.run1.bam,/data/H2009_hifi.run2.bam	/data/2009.hap1.filt.fa	/data/2009.hap2.filt.fa
BL2009	normal	/data/BL2009_ont.bam	/data/BL2009_hifi.run1.fq.gz,/data/BL2009_hifi.run2.fq.gz,/data/BL2009_hifi.run3.fq.gz	/data/2009.hap1.filt.fa	/data/2009.hap2.filt.fa
```

Notes:

- Both `ont` and `hifi` independently support comma-separated lists; you can use a single file in one column and multiple in the other (the `BL2009` row above does exactly that).
- BAM and FASTQ.gz files may be mixed within the same comma-separated list as long as they all belong to the same sample and seqtype.
- The full per-sample read set (HiFi or ONT) is concatenated and aligned together during BAM refinement, so downstream modules see one merged BAM per sample × seqtype.

## Generating `config.yaml` and `run_worklow.sh` with `setup_workflow.py`

`setup_workflow.py` writes a fully-resolved `config.yaml` from your sample sheet, image paths, and annotation files.

```bash
python3 setup_workflow.py \
    --samplesheet /path/to/samples.tsv \
    --reference /path/to/CHM13.fa \
    --hap1-satellite /path/to/2009.hap1.cenSat.bed.gz \
    --hap2-satellite /path/to/2009.hap2.cenSat.bed.gz \
    --sex male/female \
    --gtf-file /path/to/{sample}.liftoff.gtf.gz 
    --simple-repeat /path/to/{sample}.simple_repeats.bed.gz \
    --line1-bed /path/to/{sample}.LINE1.bed.gz \
    --output-dir /path/to/output \
    --output config.yaml \
    -runner run_worklow.sh \
    --force 
```

### Optional arguments

- `--profile` 
- `---singularity-bind` 

### Annotation file flags

The annotation flags map directly to the `assembly_workflow` outputs described in [Preparation.md](./Preparation.md):

| Flag | Source (assembly_workflow output) |
|------|-----------------------------------|
| `--hap1-satellite` | DNA-NN output for haplotype 1 |
| `--hap2-satellite` | CenSat output for haplotype 2 |
| `--simple-repeat` | RepeatMasker `*.simple_repeats.bed.gz` |
| `--line1-bed` | RepeatMasker `*.LINE1.bed.gz` |
| `--gtf-file` | Liftoff `*.liftoff.gtf.gz` |
| `--sex` | Sample sex (`male` / `female`) — affects sex-chromosome handling |

## Running the workflow

### Local execution

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile /path/to/config.yaml \
    --directory /path/to/output \
    --sdm apptainer \
    --apptainer-args "-B /home/user -B /data" \
    --cores 16 \
    --resources mem_mb=128000
```

- `--apptainer-args "-B ..."` must bind every host directory referenced by the sample sheet, reference genome, annotation files, and image paths.
- `--cores` and `--resources mem_mb=...` cap concurrency for local runs.

### HPC execution

PRCGAP ships ready-to-use cluster profiles in `PRCGAP/profile/`:

- `PRCGAP/profile/uge/` — UGE / SGE (qsub) profile (`config.yaml`, `qsub_submit.sh`, `qsub_status.sh`).
- `PRCGAP/profile/slurm/` — SLURM (sbatch) profile (`config.yaml`, `slurm_submit.sh`, `slurm_status.sh`).

SGE example:

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile /path/to/config.yaml \
    --directory /path/to/output \
    --profile /path/to/PRCGAP/profile/sge
```

SLURM example:

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile /path/to/config.yaml \
    --directory /path/to/output \
    --profile /path/to/PRCGAP/profile/slurm
```

### Customizing the cluster profile

If you need a profile beyond the bundled ones, you can scaffold a new one with `cookiecutter` from a Snakemake profile template (e.g. `cookiecutter gh:Snakemake-Profiles/generic`) and adjust the following keys in the resulting `config.yaml`:

- `singularity-args` — bind mounts for your filesystem (must cover reads, references, annotations, and image files).
- `jobs` — maximum number of concurrent cluster jobs.
- `latency-wait` — seconds to wait for output files after a job exits, useful on shared filesystems with delayed visibility.
- `default-resources` — cluster-side defaults (memory, runtime) that complement per-rule `resources` in `config.yaml`.

For more cluster-specific tuning (queues, accounts, GPUs), edit the submit script (`qsub_submit.sh` / `slurm_submit.sh`) in the profile directory.

## Next step

For an end-to-end walkthrough — including a tumor / normal pair, expected outputs, and sanity checks — see [Example.md](./Example.md). For workflow internals (rules, DAG, output layout), see [Workflow.md](./Workflow.md).
