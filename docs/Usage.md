# Usage

This page is the detailed companion to [Quick start](./QuickStart.md): installation, the sample-sheet format, authoring a cluster profile, and the parts of `setup_workflow.py` that need more than a table row. The exhaustive flag list lives in [Options](./Options.md).

The setup flow is:

1. **Prerequisites** — Snakemake 7.x, Apptainer, and (optionally) cookiecutter in one isolated environment.
2. **Clone the repository and pull container images** — `images/pull_images.sh` fetches every `.sif` from Docker Hub.
3. **Fetch the references** — `resource/scripts/download_reference.sh`, once per installation.
4. **(Optional but recommended) author a cluster profile** — scaffold one from the Snakemake-Profiles templates if you submit to UGE / SLURM / PBS.
5. **Generate `config.yaml` and `run_workflow.sh`** — `setup_workflow.py` writes the sample sheet, resolves every path, embeds your profile, and emits a ready-to-execute runner.
6. **Run** — `bash run_workflow.sh`, or `sbatch` / `qsub` it under a cluster profile.

## Installation

### Prerequisites

PRCGAP runs end-to-end inside Apptainer / Singularity containers, so the host needs only:

- [Snakemake](https://snakemake.readthedocs.io/) **7.32.4** — the workflow driver.
- [Apptainer](https://apptainer.org/) — the container runtime (Singularity is supported transparently).
- [cookiecutter](https://cookiecutter.readthedocs.io/) — optional, only to scaffold a cluster profile.

Plus `python3` with `pyyaml` for `setup_workflow.py`, and `samtools` / `bgzip` / `tabix` on `PATH` for the one-time reference download.

> **WARNING — Snakemake >= 8 is not supported.** Snakemake 8 changes several CLI flags (`--sdm` / `--software-deployment-method` replaces `--use-singularity`, the profile format differs) and PRCGAP has only been validated against 7.32.4. Pin the version explicitly when you create the environment.

A quick install with [mamba](https://github.com/mamba-org/mamba):

```bash
# Snakemake (+ pyyaml for setup_workflow.py) in a dedicated environment
mamba create -n PRCGAP -c conda-forge -c bioconda "snakemake>=7,<8" pyyaml

# Singularity/Apptainer — OPTIONAL: skip if you already have it (system install
# or `module load apptainer`/`singularity`)
mamba install -n PRCGAP -c conda-forge apptainer

# cookiecutter (optional, only for generating a cluster profile)
mamba install -n PRCGAP -c conda-forge cookiecutter

# Activate the environment.
mamba activate PRCGAP   # or put the env on PATH: export PATH=<env>/bin:$PATH
```

### Clone the repository and pull container images

Every PRCGAP module ships as a pre-built Docker image on Docker Hub; you do **not** need to build any image locally. `images/pull_images.sh` pulls each one and converts it to a Singularity (`.sif`) file under `PRCGAP/images/`:

```bash
git clone https://github.com/yos-sk/PRCGAP.git
cd PRCGAP/images
bash pull_images.sh
```

Installation (this `git clone` → `.sif` creation) takes about **30 minutes**, dominated by pulling and converting the container images; the exact time depends on your network bandwidth and disk speed.

`pull_images.sh` also takes arguments: `--force` re-pulls everything, and naming modules (`bash pull_images.sh clairs deepsomatic`) pulls just those.

### Container images

The script populates `images/` with one `.sif` per module:

| Image | Used by |
|-------|---------|
| `bam_refiner.sif` | BAM refinement |
| `methylation.sif` | Methylation (HiFi & ONT) |
| `copynumber.sif` | Copy number |
| `nanomonsv.sif` | nanomonsv parse / get / insert classify |
| `nanomonsv_postprocess.sif` | nanomonsv postprocess / connect / merge |
| `clairs.sif` | ClairS |
| `deepsomatic.sif` | DeepSomatic |
| `point_mutation_postprocess.sif` | ClairS / DeepSomatic post-processing (realignment, pileup, haplotyping) |
| `annotation.sif` | SV + SNV/INDEL annotation (pysam, samtools, coordconv, transanno, bgzip/tabix) |
| `dna_nn.sif` | In-workflow annotation — dna-brnn satellites |
| `liftoff.sif` | In-workflow annotation — liftoff, minimap2, gffread |
| `chain_files.sif` | In-workflow annotation — minimap2, transanno, chaintools, rustybam, paf2chain |

The last three drive the annotation PRCGAP now builds itself (see [In-workflow annotation](#in-workflow-annotation)).

> **TIP** — `setup_workflow.py` reads `--images-dir` (default: the `images/` directory next to the script) and picks up every `<tool>.sif` automatically, so you do not have to pass each image individually. Override only the images you built locally, via the corresponding `--<tool>-image` flag.

### Fetch the references

```bash
bash resource/scripts/download_reference.sh
```

One command, once per installation. It writes `resource/reference/` and builds `resource/line1/*.fa`; the file-by-file table is in [Quick start → step 3](./QuickStart.md#_3-fetch-the-references-once-per-installation).

## In-workflow annotation

PRCGAP builds the per-assembly annotation it needs from the assembly plus the CHM13 / GRCh38 references, so a run does not depend on [assembly_workflow](https://github.com/yos-sk/assembly_workflow) having been run first:

| Step | Switch | Default | Produces |
|------|--------|---------|----------|
| dna-brnn | `--run-dna-brnn` | **on** | Per-haplotype centromeric satellite BED — masks the copy-number reference |
| Tandem repeats | `--run-simple-repeat` | **on** | ULTRA tandem-repeat BED — `nanomonsv get` drops indel-like SVs inside one |
| LINE-1 | `--run-line1` | **on** | Full-length young L1HS / L1PA2–5 BED — `nanomonsv insert_classify` transduction sources |
| Chain files | `--run-chain-files` | **on** | Assembly → CHM13 / GRCh38 chains — SV / SNV / INDEL liftover and gnomAD |
| Liftoff genes | *(no switch)* | always | Gene GFF + GTF on the assembly — gene annotation and `insert_classify` |

Pass `--no-run-<step>` to turn one off and import that file instead (`--hap1-satellite` / `--hap2-satellite`, `--simple-repeat`, `--line1-bed`, `--chain-to-grch38` / `--chain-to-chm13`). When a switch is on, the generated file wins over the corresponding path key.

Four annotation resources are **not** built in-workflow — RepeatMasker, SEDEF segmental duplications, cenSat satellite subtypes, and misassembly tracks. They are optional annotation columns; supply them from assembly_workflow if you want them. See [Preparation](./Preparation.md).

## Sample sheet

PRCGAP reads samples from a TSV file with one row per sample. Tumor and normal are separate rows that share the assembly paths.

**The recommended way to produce it is `setup_workflow.py` itself.** Passing any of the pair options (`--tumor`, `--normal`, `--assembly-hap1`, `--assembly-hap2`, or any of the read flags) makes `--samplesheet` an *output*: the script validates the entries, absolutises the data paths, and writes the canonical columns before generating the config.

```bash
python3 setup_workflow.py \
    --samplesheet config/samples.tsv \
    --tumor  {tumor_name}  --tumor-ont  /data/{tumor}_ont.bam  --tumor-hifi  /data/{tumor}_hifi.bam \
    --normal {normal_name} --normal-ont /data/{normal}_ont.bam --normal-hifi /data/{normal}_hifi.bam \
    --assembly-hap1 /data/{normal}.hap1.fa --assembly-hap2 /data/{normal}.hap2.fa \
    ...   # the rest of the configuration; see Quick start
```

Omit **all** the pair options and `--samplesheet` is read as-is, so a sheet you wrote by hand still works.

`--tumor-ont` / `--tumor-hifi` / `--normal-ont` / `--normal-hifi` are repeatable and also accept comma-separated lists when a sample spans multiple files (see [Multiple input files per sample](#multiple-input-files-per-sample)). Two more flags matter here: `--no-check-exists` when the data lives on a cluster and is not visible from the login node, and `--no-absolutize` to keep the paths as given.

Columns:

| Column | Required | Description |
|--------|----------|-------------|
| `sample` | yes | Unique sample identifier |
| `type` | yes | `tumor` or `normal` |
| `ont` | no | Path(s) to ONT data (bam or fastq.gz). Multiple files are supported — a single comma-separated value, no spaces. |
| `hifi` | no | Path(s) to HiFi data (bam or fastq.gz). Same comma-separated form. |
| `assembly_hap1` | yes | Path to the haplotype 1 assembly (FASTA) — the same path for tumor and normal of a pair. |
| `assembly_hap2` | yes | Path to the haplotype 2 assembly (FASTA) — the same path for tumor and normal of a pair. |

`ont` and `hifi` are each optional, but **every sample must have at least one of them**. That is what makes HiFi-only and ONT-only runs work; see [Sequencing types](#sequencing-types-hifi-only-ont-only-and-both).

Example (`samples.tsv`):

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
{tumor_name}	tumor	/data/{tumor}_ont.bam	/data/{tumor}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
{normal_name}	normal	/data/{normal}_ont.bam	/data/{normal}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
```

For tumor / normal pairs, **both samples must use the same haplotype assemblies** — typically those built from the matched normal.

### One pair per run

A run is one tumor / normal pair on one assembly. The per-assembly annotation in `config.yaml` is global, so `setup_workflow.py` rejects a sheet with more than one normal, or with samples pointing at different assembly pairs. Run distinct pairs separately, each with its own config, sample sheet, and `--output-dir`.

### Sequencing types: HiFi-only, ONT-only, and both

Leave the column (or the flag) empty for a sequencing type you do not have.

```
# HiFi-only pair — the ont column is present but empty
sample	type	ont	hifi	assembly_hap1	assembly_hap2
{tumor_name}	tumor		/data/{tumor}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
{normal_name}	normal		/data/{normal}_hifi.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
```

How the workflow adapts:

- **Per-sample rules** (BAM refinement, methylation) run for every seqtype that sample has.
- **Tumor / normal rules** (nanomonsv, copy number, point mutations) run only for seqtypes present in **both** the tumor and its paired normal — a matched pair of BAMs is required.
- **Point mutations** default to `--mutation-seqtypes primary`: one seqtype only, HiFi when both are present. SNV/INDEL calling is validated on HiFi, and on a HiFi+ONT sample the ONT arm is the more expensive of the two while adding calls without HiFi support. Pass `--mutation-seqtypes all` to call on every shared seqtype.
- **Copy number** always uses the primary shared seqtype.
- **`--run-nanomonsv-merge`** (HiFi + ONT SV merge) only fires when both seqtypes are present.

::: warning ONT and ClairS
`--clairs-model` defaults to `hifi_sequel2`. On ONT data with `--mutation-caller clairs` or `both`, set it explicitly — e.g. `--clairs-model ont_r10_dorado_sup_5khz_ssrs`. It applies to every seqtype ClairS runs on.
:::

### Multiple input files per sample

The `ont` and `hifi` columns each accept **one or more file paths in a single TSV cell**. When a sample has been sequenced across multiple runs, list every path joined by commas — **no whitespace around the commas, no quoting, and the entire list stays in one column**.

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
{tumor_name}	tumor	/data/{tumor}_ont.run1.bam,/data/{tumor}_ont.run2.bam	/data/{tumor}_hifi.run1.bam,/data/{tumor}_hifi.run2.bam	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
{normal_name}	normal	/data/{normal}_ont.bam	/data/{normal}_hifi.run1.fq.gz,/data/{normal}_hifi.run2.fq.gz	/data/{normal}.hap1.fa	/data/{normal}.hap2.fa
```

Notes:

- Both `ont` and `hifi` independently support comma-separated lists; you can use a single file in one column and multiple in the other.
- bam and fastq.gz files may be mixed within the same comma-separated list as long as they all belong to the same sample and seqtype.
- The full per-sample read set is concatenated and aligned together during BAM refinement, so downstream modules see one merged BAM per sample × seqtype.

## (Optional but recommended) Author a cluster profile with `cookiecutter`

For users working with high-performance computing (HPC) clusters, we **strongly recommend** creating a Snakemake profile to manage job submission. Bind mounts, queues, account flags, and per-job resource caps differ significantly between sites, so PRCGAP does not ship a profile — you scaffold one for your own cluster. Once the profile directory exists, `setup_workflow.py --profile <path>` absolutises every path-valued key and embeds the profile into the generated runner script.

The Snakemake-Profiles project ships [cookiecutter](https://cookiecutter.readthedocs.io/) templates for every major scheduler. The SLURM template is the most actively maintained one; SGE/UGE, LSF, PBS, and a generic fallback are also available under [`Snakemake-Profiles` on GitHub](https://github.com/Snakemake-Profiles).

### Scaffold the profile

We recommend writing the generated profile under a top-level `profile/` directory inside your PRCGAP working tree so that `--profile profile/<profile_name>` paths stay short:

```bash
template="gh:Snakemake-Profiles/slurm"

cookiecutter \
    --output-dir profile \
    $template
```

(Use `gh:Snakemake-Profiles/sge`, `…/lsf`, `…/pbs-torque`, or `…/generic` instead of `slurm` for other schedulers.)

### Interactive prompts walkthrough

Cookiecutter then asks **17 questions** in sequence. Suggested answers for a SLURM-based PRCGAP deployment are shown alongside each prompt; press `Enter` to accept the default in `(parens)`. Adjust to taste — every answer ends up in `profile/<profile_name>/config.yaml` and can be edited afterwards.

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
[8/17]  latency_wait (5):                            # bump to 60–120 on Lustre / NFS
[9/17]  Select print_shell_commands                  # ► 1 (False) — keep snakemake's log compact
[10/17] sbatch_defaults:                             # site-specific, e.g. "partition=cpuq account=myacct"
        # other options (qos, time, mail-user, …) can also be appended here as space-separated key=value
[11/17] cluster_sidecar_help:                        # informational; press Enter
[12/17] Select cluster_sidecar                       # ► 1 (yes) on Snakemake 7.x — uses one sidecar
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
profile/<profile_name>/
├── CookieCutter.py        # template-helper module imported by the wrappers below
├── config.yaml            # snakemake profile config — edit this for site tuning
├── settings.json          # captures the answers you gave to cookiecutter (regenerate-friendly)
├── slurm-jobscript.sh     # per-job shell wrapper (executed by sbatch)
├── slurm-sidecar.py       # batched squeue/sacct polling (when cluster_sidecar=yes)
├── slurm-status.py        # job-status query script
├── slurm-submit.py        # the actual sbatch wrapper Snakemake invokes
└── slurm_utils.py         # shared helpers for the above
```

`setup_workflow.py` reads `settings.json` to find the partition, and emits it as `#SBATCH -p` in the generated runner so the driver job lands on the same partition as its rules.

> **TIP** — re-running `cookiecutter $template --output-dir profile -f --replay` regenerates the same profile non-interactively (using `settings.json`); useful for sharing the recipe across teammates without re-typing the 17 answers.

### Pin per-job cores to the allocation

By default the generated `slurm-jobscript.sh` launches each job's in-container Snakemake with `--cores all`, which makes it grab **every** core on the compute node rather than the `--cpus-per-task` the scheduler actually allocated. Overwrite the jobscript so it rewrites `--cores all` to the allocated core count (`$SLURM_CPUS_PER_TASK`). Re-apply this after each profile regeneration, since cookiecutter overwrites the file:

```bash
cat > profile/slurm/slurm-jobscript.sh <<'EOF'
#!/bin/bash
# properties = {properties}
exec_job=$(cat <<'SMK_EXEC_JOB'
{exec_job}
SMK_EXEC_JOB
)
ncores="${{SLURM_CPUS_PER_TASK:-1}}"
exec_job=$(printf '%s' "$exec_job" | sed -E "s/--cores '?all'?/--cores $ncores/")
eval "$exec_job"
EOF
```

For SGE/UGE use the same body but read the allocation from `$NSLOTS` and write it to `profile/sge/sge-jobscript.sh` instead.

This also matters for the caller memory defaults: `clairs` / `deepsomatic` size their TensorFlow shards from the visible core count, so without core pinning they need considerably more memory than the defaults in [Options → Per-rule resources](./Options.md#per-rule-resources).

## Generating `config.yaml` and `run_workflow.sh`

`setup_workflow.py` writes a fully-resolved `config.yaml` from your sample sheet, image paths, references, and annotation files, plus a runner script that invokes Snakemake with the right flags. The minimal invocation is in [Quick start → step 5](./QuickStart.md#_5-configure); every flag is catalogued in [Options](./Options.md).

Two notes on how paths are handled:

- Snakemake runs with `cwd = --output-dir`, so every path in `config.yaml` is absolutised at generation time. Relative paths on the command line are resolved against **your current directory**, not the output directory.
- Absolutisation uses `os.path.abspath`, which does **not** follow symlinks: a path like `/home/<user>` stays in its user-facing form rather than becoming its target. That keeps it consistent with what you bind-mount into the container — but see the symlink note under [`--singularity-bind`](#bind-mounts).

### Handing off the cluster profile

`--profile` is how the cookiecutter profile from the [previous section](#optional-but-recommended-author-a-cluster-profile-with-cookiecutter) gets wired into your run. Pass the **directory** that contains `config.yaml` (e.g. `profile/prcgap-slurm/`), and `setup_workflow.py` will:

1. Absolutise the profile path, so the runner works regardless of where you invoke it from.
2. Rewrite any **path-valued keys inside `<profile>/config.yaml`** (`jobscript`, `cluster`, `cluster-status`, `cluster-cancel`, and the v8 `cluster-generic-*` equivalents) to absolute paths. Snakemake resolves these relative to the current working directory rather than to the profile directory, so without this rewrite they would break under `--directory <output_dir>`.
3. Emit `snakemake --profile <absolute path> …` inside `run_workflow.sh`.
4. Give the runner a scheduler header — `#SBATCH` when the profile directory name contains `slurm`, `#$` when it contains `sge` or `uge` — so the snakemake driver itself runs as a batch job. Submit it with `sbatch` / `qsub` rather than `bash`. Tune the driver with `--driver-time` and `--driver-mem`.

When `--profile` is omitted, `setup_workflow.py` produces a local-execution runner (`snakemake -j <jobs> --use-singularity …`) that you run with `bash`.

```bash
python3 setup_workflow.py \
    ... \
    --profile profile/slurm \
    --jobs 64                 # max concurrent cluster jobs (matches `jobs:` in the profile)
```

If your site needs setup the generated script cannot know — a module load, a PATH for snakemake — add it with `--runner-preamble`, which is repeatable:

```bash
python3 setup_workflow.py \
    ... \
    --runner-preamble 'module load apptainer' \
    --runner-preamble 'export PATH=~/miniconda3/envs/snakemake7/bin:$PATH'
```

### Bind mounts

Snakemake launches each rule inside Apptainer / Singularity, and only the host paths explicitly bind-mounted into the container are visible to the in-container processes. The generated runner forwards this list verbatim to Snakemake as `--singularity-args "-B <paths> -e"`.

```bash
python3 setup_workflow.py \
    ... \
    --singularity-bind "/data,/scratch,/home/me/refs"
```

Rules-of-thumb for what to bind:

- Every directory referenced by the **sample sheet** (ONT / HiFi bams or fastqs, `assembly_hap1`, `assembly_hap2`).
- The **references** (`--chm13-fasta`, `--grch38-fasta`, `--grch38-gtf`, `--chm13-censat`, `--grch38-centromeres`, `--grch38-exclusions`, `--mane-summary`).
- Every **annotation resource** path you passed (`--repeat-masker-bed`, `--segdup-bed`, `--censat-bed`, `--misassembly-hap*-bed`, `--cancer-gene-census-tsv`, `--cmrg-gene-list`, `--gnomad-*`, and the `--chain-to-*` / `--*-satellite` / `--simple-repeat` / `--line1-bed` paths if you import rather than generate them).
- The **PRCGAP repository itself** — `--images-dir` holds the `.sif` files, `--workflow-dir` the rules and scripts, and `resource/line1/` the LINE-1 models.
- The **output directory** (`--output-dir`).
- Any **symlink targets** — if a path is a symlink, bind both the symlink's location *and* the real path it points to. Some rules resolve symlinks internally (`assembly_bwa_index` uses `readlink -f`), so the target form has to be visible too. `realpath` is useful for spotting these. A common case is a home directory that is itself a symlink:

  ```bash
  SING_BIND="$HOME"
  HOME_REAL=$(readlink -f "$HOME")
  [ "$HOME_REAL" != "$HOME" ] && SING_BIND="$HOME,$HOME_REAL"
  ```

Format notes:

- The value is a **comma-separated** list of host paths; no spaces, no quotes around the value itself.
- A single host path is enough — Apptainer mounts it read-write at the same path inside the container by default.
- For read-only mounts, use the explicit `src:dst:ro` form (e.g. `--singularity-bind "/data:/data:ro,/scratch"`); the runner forwards it unchanged.
- Bind paths must exist on the host before snakemake starts; non-existent paths cause container startup to fail.

If you need a path bound only inside a subset of rules, set it instead via that profile's `singularity-args` and rely on `--profile`.

### Building only part of the pipeline

`--targets` bakes default Snakemake targets into the runner, so it builds only those. Targets are relative to `--output-dir`:

```bash
python3 setup_workflow.py ... --targets "copynumber/{tumor}/output/{tumor}.copynumber.png"
```

Targets passed on the runner's own command line still override the baked-in ones, so `bash run_workflow.sh <other/target>` always works.

### A full invocation with every annotation resource

```bash
python3 setup_workflow.py \
    --samplesheet config/samples.tsv \
    --tumor  {tumor}  --tumor-hifi  /data/{tumor}.hifi.bam  --tumor-ont  /data/{tumor}.ont.bam \
    --normal {normal} --normal-hifi /data/{normal}.hifi.bam --normal-ont /data/{normal}.ont.bam \
    --assembly-hap1 /data/{normal}.hap1.fa \
    --assembly-hap2 /data/{normal}.hap2.fa \
    --sex male \
    --chm13-fasta        resource/reference/chm13v2.0_maskedY_rCRS.fa \
    --grch38-fasta       resource/reference/GRCh38.d1.vd1.fa \
    --grch38-gtf         resource/reference/Homo_sapiens.GRCh38.Ensembl.112.chr.format.gtf \
    --chm13-censat       resource/reference/chm13v2.0_censat_v2.1.bed.gz \
    --grch38-centromeres resource/reference/centromeres.txt.gz \
    --grch38-exclusions  resource/reference/GCA_000001405.15_GRCh38_GRC_exclusions_T2Tv2.bed \
    --mane-summary       resource/reference/MANE.GRCh38.v1.3.summary.txt.gz \
    --repeat-masker-bed      /path/to/{normal}.rmsk.bed.gz \
    --segdup-bed             /path/to/{normal}.segdup.bed.gz \
    --censat-bed             /path/to/{normal}.censat.bed.gz \
    --misassembly-hap1-bed   /path/to/{normal}.hap1.misassembly.bed.gz \
    --misassembly-hap2-bed   /path/to/{normal}.hap2.misassembly.bed.gz \
    --cancer-gene-census-tsv /path/to/cancer_gene_census.tsv \
    --cmrg-gene-list         /path/to/cmrg_genes.list \
    --gnomad-bed             /path/to/gnomad.v4.1.sv.sites.bed.gz \
    --gnomad-vcf             /path/to/gnomad.genomes.v4.1.sites.vcf.bgz \
    --mutation-caller both \
    --output-dir /path/to/output \
    --output config/config.yaml \
    --runner run_workflow.sh \
    --singularity-bind "$HOME" \
    --profile profile/slurm \
    --jobs 64
# add --force (-f) when re-generating over an existing config / runner / sheet
```

Every annotation flag here is optional: dropping a line simply omits that annotation column. See [Preparation](./Preparation.md) for where each file comes from.

## Running the workflow

```bash
bash run_workflow.sh          # local execution
sbatch run_workflow.sh        # SLURM profile
qsub   run_workflow.sh        # SGE / UGE profile
```

The runner is generated with `--rerun-triggers mtime --rerun-incomplete --keep-going`, so re-running it after a failure resumes rather than restarting, and one failed branch does not stop the others.

On success PRCGAP deletes the scratch a finished run no longer needs — every `workspace/`, the caller scatter directories, `bwa_index/`, `copynumber/reference/`, and the per-rule copies of `reference.fa` — and prints what it removed. A failed or interrupted run keeps everything for inspection. Pass `--debug` to `setup_workflow.py` to keep it in all cases.

## Next step

For an end-to-end walkthrough — a real tumor / normal pair, the files a finished run produces, and the copy-number plot — see [Example](./Example.md). For workflow internals (rules, DAG, output layout), see [Workflow](./Workflow.md).
