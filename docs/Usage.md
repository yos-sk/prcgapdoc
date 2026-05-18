# Usage

This page covers how to install PRCGAP, author a sample sheet, generate `config.yaml`, and run the workflow locally or on a cluster. It assumes that the personalized reference genome and annotation files described in [Preparation.md](./Preparation.md) are already available.

## Installation

PRCGAP runs end-to-end inside Apptainer / Singularity containers, so the host only needs a handful of tools to drive the workflow. The setup flow is:

1. **Prerequisites** — install Snakemake 7.x, Apptainer, and (optionally) cookiecutter, ideally in one isolated environment.
2. **Clone the repository and pull container images** — `git clone` + `images/pull_images.sh` fetch every `.sif` from Docker Hub.
3. **(Optional but recommended) Author a cluster profile** — scaffold one from the Snakemake-Profiles templates if you submit to UGE/SLURM/PBS.
4. **Author the sample sheet** — one TSV row per sample (tumor and normal go in separate rows that share assembly paths).
5. **Generate `config.yaml` and `run_workflow.sh`** — `setup_workflow.py` resolves every path, embeds your profile, and emits a ready-to-execute runner script.
6. **Run** — `bash run_workflow.sh` (or invoke `snakemake` directly).

The sections below walk through each step in order.

### Prerequisites

PRCGAP needs three host-side tools:

- [Snakemake](https://snakemake.readthedocs.io/) **7.32.4** — the workflow language driver.
- [Apptainer](https://apptainer.org/) — the container runtime (Singularity is also supported transparently).
- [cookiecutter](https://cookiecutter.readthedocs.io/) — optional, only needed when scaffolding a fresh cluster profile (step 3 above).

> **WARNING — Snakemake 8.x is not supported.** Snakemake 8 changes several CLI flags (`--sdm` / `--software-deployment-method` replaces `--use-singularity`, profile format differs, etc.) and PRCGAP has only been validated against 7.32.4. Pin the version explicitly when you create the environment.

### Clone the repository and pull container images

Every PRCGAP module ships as a pre-built Docker image on Docker Hub; you do **not** need to build any image locally. `images/pull_images.sh` pulls each one and converts it to a Singularity (`.sif`) file under `PRCGAP/images/`:

```bash
git clone https://github.com/yos-sk/PRCGAP.git
cd PRCGAP
bash images/pull_images.sh
```

The script populates `images/` with one `.sif` per module:

| Image | Used by |
|-------|---------|
| `bam_refiner.sif` | BAM Refiner |
| `methylation.sif` | Methylation (HiFi & ONT) |
| `copynumber.sif` | Copy Number |
| `nanomonsv.sif` | Nanomonsv parse / get / insert classify |
| `nanomonsv_postprocess.sif` | Nanomonsv postprocess / connect / merge |
| `clairs.sif` | ClairS |
| `deepsomatic.sif` | DeepSomatic |
| `point_mutation_postprocess.sif` | ClairS / DeepSomatic post-processing (realignment, pileup, haplotyping) |
| `annotation.sif` | SV + SNV/INDEL annotation (pysam, samtools, coordconv, transanno, bgzip/tabix) |

> **TIP** — `setup_workflow.py` reads `--images-dir` (default `images/`) and picks up every `<tool>.sif` automatically, so you do not have to pass each image individually. Override only the images you have built locally via the corresponding `--<tool>-image` flag.

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
{tumor_name}	tumor	/data/{tumor}_ont.bam	/data/{tumor}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.filt.fa
{normal_name}	normal	/data/{normal}_ont.bam	/data/{normal}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
```

### Multiple input files per sample

The `ont` and `hifi` columns each accept **one or more file paths in a single TSV cell**. When a sample has been sequenced across multiple runs (or split into multiple BAM/FASTQ files for any other reason), list every path joined by commas — **no whitespace around the commas, no quoting, and the entire list stays in one column**.

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
{tumor_name}	tumor	/data/{tumor}_ont.run1.bam,/data/{tumor}_ont.run2.bam	/data/{tumor}_hifi.run1.bam,/data/{tumor}_hifi.run2.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
{normal_name}	normal	/data/{normal}_ont.bam	/data/{normal}_hifi.run1.fq.gz,/data/{normal}_hifi.run2.fq.gz,/data/{normal}_hifi.run3.fq.gz	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
```

Notes:

- Both `ont` and `hifi` independently support comma-separated lists; you can use a single file in one column and multiple in the other (the `{normal_name}` row above does exactly that).
- BAM and FASTQ.gz files may be mixed within the same comma-separated list as long as they all belong to the same sample and seqtype.
- The full per-sample read set (HiFi or ONT) is concatenated and aligned together during BAM refinement, so downstream modules see one merged BAM per sample × seqtype.

## (Optional but recommended) Author a cluster profile with `cookiecutter`

For users working with high-performance computing (HPC) clusters, we **strongly recommend** creating a Snakemake profile to manage job submission. Bind mounts, queues, account flags, and per-job resource caps differ significantly between sites, and the bundled `PRCGAP/profile/uge` / `PRCGAP/profile/slurm` profiles are starting points rather than drop-in defaults. Once the profile directory exists, `setup_workflow.py --profile <path>` absolutises every path-valued key and embeds the profile into the generated runner script.

The Snakemake-Profiles project ships [cookiecutter](https://cookiecutter.readthedocs.io/) templates for every major scheduler. The SLURM template is the most actively maintained one; SGE/UGE, LSF, PBS, and a generic fallback are also available under [`Snakemake-Profiles` on GitHub](https://github.com/Snakemake-Profiles).

### Scaffold the profile

We recommend writing the generated profile under a top-level `config/` directory inside your PRCGAP working tree so that `--profile config/<profile_name>` paths stay short and version-controllable:

```bash
template="gh:Snakemake-Profiles/slurm"

cookiecutter \
    --output-dir profile \
    $template
```

(Use `gh:Snakemake-Profiles/sge`, `…/lsf`, `…/pbs-torque`, or `…/generic` instead of `slurm` for other schedulers.)

### Interactive prompts walkthrough

Cookiecutter then asks **17 questions** in sequence. Suggested answers for a SLURM-based PRCGAP deployment are shown alongside each prompt; press `Enter` to accept the default in `(parens)`. Adjust to taste — every answer ends up in `config/<profile_name>/config.yaml` and can be edited afterwards.

```
[1/17]  profile_name (slurm):                        # accept default or e.g. prcgap-slurm
[2/17]  Select use_singularity                       # ► 2 (True)  — PRCGAP runs every rule in a container
        1 - False
        2 - True
[3/17]  Select use_conda                             # ► 1 (False) — PRCGAP does not use conda envs
        1 - False
        2 - True
[4/17]  jobs (500):                                  # max concurrent SLURM jobs; 64–500 is typical
[5/17]  restart_times (0):                           # 1 is reasonable; retries transient SLURM failures once
[6/17]  max_status_checks_per_second (10):           # keep default unless your scheduler is rate-limited
[7/17]  max_jobs_per_second (10):                    # keep default
[8/17]  latency_wait (5):                            # bump to 60–120 on Lustre / NFS (see note below)
[9/17]  Select print_shell_commands                  # ► 1 (False) — keep snakemake's log compact
[10/17] sbatch_defaults:                             # site-specific, e.g. "partition=cpuq account=myacct"
        # other options (qos, time, mail-user, …) can also be appended here as space-separated key=value
[11/17] cluster_sidecar_help:                        # informational; press Enter
[12/17] Select cluster_sidecar                       # ► 2 (yes) on Snakemake 7.x — uses one sidecar
        1 - yes                                       #     process to batch squeue/sacct calls
        2 - no
[13/17] cluster_name:                                # optional free-form label; leave empty unless you
                                                     #   run multiple clusters from the same login node
[14/17] cluster_jobname ({rule}.{jobid}):            # accept default; expands per job
[15/17] cluster_logpath (logs/slurm/{rule}/%j):      # accept default; paths are created automatically
[16/17] cluster_config_help:                         # informational; press Enter
[17/17] cluster_config:                              # leave empty — deprecated in favor of resources
```

### Generated layout

The above run produces:

```
config/<profile_name>/
├── CookieCutter.py        # template-helper module imported by the wrappers below
├── config.yaml            # snakemake profile config — edit this for site tuning (see below)
├── settings.json          # captures the answers you gave to cookiecutter (regenerate-friendly)
├── slurm-jobscript.sh     # per-job shell wrapper (executed by sbatch)
├── slurm-sidecar.py       # batched squeue/sacct polling (when cluster_sidecar=yes)
├── slurm-status.py        # job-status query script
├── slurm-submit.py        # the actual sbatch wrapper Snakemake invokes
└── slurm_utils.py         # shared helpers for the above
```

> **TIP** — re-running `cookiecutter $template --output-dir config -f --replay` regenerates the same profile non-interactively (using `settings.json`); useful for sharing the recipe across teammates without re-typing the 17 answers.

### Post-generation editing — example: SLURM + Lustre site

The interactive answers cover the basics; site-specific tuning then happens in `config/<profile_name>/config.yaml`. Lustre is a parallel filesystem common at HPC sites, and it has two characteristics that matter for Snakemake:

1. **File-visibility latency between nodes.** A job that writes an output on one compute node may take a few seconds to a few tens of seconds before that file is visible on another node (or on the login node where Snakemake itself runs). The default `latency-wait` (5 s) is usually too short.
2. **Bind mounts must cover every Lustre tree the workflow touches** — reads, references, annotations, images, *and* the run directory itself, otherwise Apptainer / Singularity will see them as missing inside the container.

A minimal `<profile>/config.yaml` for a SLURM + Lustre site looks like:

```yaml
# <profile>/config.yaml
cluster: "sbatch
  --parsable
  --partition={resources.partition}
  --account=my_account
  --cpus-per-task={threads}
  --mem={resources.mem_mb}
  --time={resources.runtime}
  --job-name=smk-{rule}-{wildcards}
  --output=logs/cluster/{rule}/{wildcards}.%j.out
  --error=logs/cluster/{rule}/{wildcards}.%j.err"

cluster-status: "./slurm_status.sh"
cluster-cancel: "scancel"

jobs: 64                   # max concurrent SLURM jobs
latency-wait: 120          # seconds — bumped from default 5 for Lustre
restart-times: 1
keep-going: True
rerun-incomplete: True
use-singularity: True
singularity-args: "-B /lustre,/lustre/scratch,/lustre/projects,/home -e"

default-resources:
  - partition=cpu
  - mem_mb=8000
  - runtime=240          # minutes
```

- `singularity-args` lists every Lustre mount root you need visible inside the container. Add any extra trees referenced by your sample sheet / config / reference paths.
- `latency-wait: 120` is a conservative starting point on Lustre; raise further if you see `MissingOutputException` warnings on healthy jobs.
- `default-resources` are cluster-side fallbacks; per-rule `threads` / `mem_mb` from `config.yaml` (set via `setup_workflow.py --*-threads / --*-mem-mb`) override these.

Once the profile directory exists, hand it to `setup_workflow.py --profile <path>`; the generated runner script will invoke `snakemake --profile <absolute path>` automatically.

> Sites without Lustre (NFS, BeeGFS, local-only): the same profile works — leave `singularity-args` pointing at your shared roots and tune `latency-wait` to what your filesystem actually needs.

## Generating `config.yaml` and `run_worklow.sh` with `setup_workflow.py`

`setup_workflow.py` writes a fully-resolved `config.yaml` from your sample sheet, image paths, and annotation files.

```bash
python3 setup_workflow.py \
    --samplesheet /path/to/samples.tsv \
    --reference /path/to/CHM13.fa \
    --hap1-satellite /path/to/{sample}.hap1_dna-brnn.bed.gz \
    --hap2-satellite /path/to/{sample}.hap2_dna-brnn.bed.gz \
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

#### `--profile <path>` — hand off the cookiecutter-generated profile

`--profile` is how the cookiecutter profile from the [previous section](#optional-but-recommended-author-a-cluster-profile-with-cookiecutter) gets wired into your run. Pass the **directory** that contains `config.yaml` (e.g. `config/prcgap-slurm/` if you scaffolded with `--output-dir config`), and `setup_workflow.py` will:

1. Absolutise the profile path (the runner script uses an absolute path so it works regardless of where you invoke it from).
2. Rewrite any **path-valued keys inside `<profile>/config.yaml`** (`jobscript`, `cluster`, `cluster-status`, `cluster-cancel`, and the v8 `cluster-generic-*` equivalents) to absolute paths. Snakemake resolves these relative to the current working directory rather than to the profile directory, so without this rewrite they would break under `--directory <output_dir>`.
3. Emit `snakemake --profile <absolute path> …` inside `run_workflow.sh`.

When `--profile` is omitted, `setup_workflow.py` produces a local-execution runner (`snakemake -j <jobs> --use-singularity …`).

```bash
# After cookiecutter has written config/prcgap-slurm/
python3 setup_workflow.py \
    ... \
    --profile config/prcgap-slurm \
    --jobs 64                                  # max concurrent SLURM jobs (matches `jobs:` in the profile)
```

#### `--singularity-bind <comma-separated paths>` — local-run bind mounts

Snakemake will launch each rule inside Apptainer / Singularity, and only the host paths explicitly bind-mounted into the container are visible to the in-container processes. The generated runner script forwards this list verbatim to Snakemake as `--singularity-args "-B <paths> -e"`.

```bash
python3 setup_workflow.py \
    ... \
    --singularity-bind "/data,/scratch,/home/me/refs"
```

Rules-of-thumb for what to bind:

- Every directory referenced by **`samplesheet.tsv`** (ONT / HiFi BAMs or FASTQs, `assembly_hap1`, `assembly_hap2`).
- The **reference** (`--chm13-fasta`, `--grch38-fasta`).
- Every **annotation resource** path you passed (`--gff-file`, `--chain-to-*`, `--repeat-masker-bed`, `--segdup-bed`, `--censat-bed`, `--misassembly-hap*-bed`, `--cancer-gene-census-tsv`, `--cmrg-gene-tsv`, `--gencode-transcript-bed`, `--gnomad-*`).
- The **images directory** holding the `.sif` files (`--images-dir`, default `images/`).
- The **output directory** (`--output-dir`).
- Any **symlink targets** — if a file in your sample sheet is a symlink, you need to bind both the symlink's location *and* the real path it points to. Tools like `realpath` are useful for spotting these (`realpath samples.tsv ... | xargs -n1 dirname | sort -u`).

Format notes:

- The value is a **comma-separated** list of host paths; no spaces, no quotes around the value itself.
- A single host path is enough — Apptainer mounts it read-write at the same path inside the container by default.
- For read-only mounts, use the explicit `src:dst:ro` form (e.g. `--singularity-bind "/data:/data:ro,/scratch"`); the runner forwards it unchanged.
- Bind paths must exist on the host before snakemake starts; non-existent paths cause container startup to fail.

If you need a path bound only inside a subset of rules, set it instead via that profile's `singularity-args` and rely on `--profile`.

### Annotation file flags

The annotation flags map directly to the outputs described in [Preparation.md](./Preparation.md):

| Flag | Source (assembly_workflow output) |
|------|-----------------------------------|
| `--hap1-satellite` | DNA-NN output for haplotype 1 |
| `--hap2-satellite` | DNA-NN  output for haplotype 2 |
| `--simple-repeat` | RepeatMasker `*.simple_repeats.bed.gz` |
| `--line1-bed` | RepeatMasker `*.LINE1.bed.gz` |
| `--gtf-file` | Liftoff `*.liftoff.gtf.gz` (consumed by `nanomonsv insert_classify`) |
| `--sex` | Sample sex (`male` / `female`) — affects sex-chromosome handling |

### Variant-annotation resource flags (optional)

These flags drive the SV and SNV/INDEL annotation modules. **All keys are optional**; if a flag is left empty (the default), the corresponding annotation column is silently skipped — the DAG still resolves, the chain just emits fewer columns.

| Flag | config key | Used by |
|------|------------|---------|
| `--gff-file` | `gff_file` | SV / SNV / INDEL gene annotation (tabix-indexed liftoff GFF; the SV BED is derived on the fly) |
| `--chain-to-grch38` | `chain_to_grch38` | SV / SNV / INDEL liftover to GRCh38 |
| `--chain-to-chm13` | `chain_to_chm13` | SV / SNV / INDEL liftover to CHM13 |
| `--repeat-masker-bed` | `repeat_masker_bed` | SV / SNV / INDEL RepeatMasker overlap |
| `--segdup-bed` | `segdup_bed` | SV / SNV / INDEL segmental-duplication overlap |
| `--censat-bed` | `censat_bed` | SV / SNV / INDEL centromere/satellite overlap |
| `--misassembly-hap1-bed` | `misassembly_hap1_bed` | SV / SNV / INDEL misassembly overlap (hap1) |
| `--misassembly-hap2-bed` | `misassembly_hap2_bed` | SV / SNV / INDEL misassembly overlap (hap2) |
| `--cancer-gene-census-tsv` | `cancer_gene_census_tsv` | SV / SNV / INDEL gene-level cancer annotation |
| `--cmrg-gene-tsv` | `cmrg_gene_tsv` | SNV / INDEL CMRG gene annotation |
| `--gencode-transcript-bed` | `gencode_transcript_bed` | SNV / INDEL GENCODE transcript overlay |
| `--gnomad-bed` | `gnomad_bed` | SV gnomAD annotation (requires `--chain-to-grch38`) |
| `--gnomad-vcf` | `gnomad_vcf` | SNV / INDEL gnomAD annotation (requires `--chain-to-grch38`) |
| `--grch38-fasta` | `grch38_fasta` | GRCh38 FASTA used as transanno `--query` for INDEL liftover (requires `--chain-to-grch38`) |

Example invocation with the full annotation set:

```bash
python3 setup_workflow.py \
    --samplesheet /path/to/samples.tsv \
    --chm13-fasta /path/to/CHM13.fa \
    --hap1-satellite /path/to/{sample}.hap1_dna-brnn.bed.gz \
    --hap2-satellite /path/to/{sample}.hap2_dna-brnn.bed.gz \
    --simple-repeat /path/to/{sample}.simple_repeats.bed.gz \
    --line1-bed /path/to/{sample}.LINE1.bed.gz \
    --gtf-file /path/to/{sample}.liftoff.gtf.gz \
    --sex male \
    --gff-file /path/to/{sample}.liftoff.gff.gz \
    --chain-to-grch38 /path/to/{sample}.to_grch38.chain \
    --chain-to-chm13  /path/to/{sample}.to_chm13.chain \
    --repeat-masker-bed /path/to/{sample}.rmsk.bed.gz \
    --segdup-bed /path/to/{sample}.segdup.bed.gz \
    --censat-bed /path/to/{sample}.censat.bed.gz \
    --misassembly-hap1-bed /path/to/{sample}.hap1.misassembly.bed \
    --misassembly-hap2-bed /path/to/{sample}.hap2.misassembly.bed \
    --cancer-gene-census-tsv /path/to/cancer_gene_census.tsv \
    --cmrg-gene-tsv /path/to/cmrg_genes.tsv \
    --gencode-transcript-bed /path/to/gencode.transcript.bed.gz \
    --gnomad-bed /path/to/gnomad_sv.bed.gz \
    --gnomad-vcf /path/to/gnomad.vcf.gz \
    --grch38-fasta /path/to/GRCh38.fa \
    --output-dir /path/to/output \
    --output config.yaml \
    --runner run_workflow.sh \
    --force
```

## Running the workflow

```
bash run_workflow.sh
```

## Next step

For an end-to-end walkthrough — including a tumor / normal pair, expected outputs, and sanity checks — see [Example.md](./Example.md). For workflow internals (rules, DAG, output layout), see [Workflow.md](./Workflow.md).
