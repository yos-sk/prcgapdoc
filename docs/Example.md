# Example

This page walks through an end-to-end PRCGAP run on a public tumor / normal pair, restricted to **chromosome 20** to keep the dataset small enough to drive on a single workstation. The sample is **HG008** — a broadly-consented matched tumor / normal pair (pancreatic ductal adenocarcinoma cell line and matched normal tissues) developed by NIST's [Cancer Genome in a Bottle](https://www.nist.gov/programs-projects/cancer-genome-bottle) project and characterised in [McDaniel *et al.*, *Scientific Data* (2025)](https://doi.org/10.1038/s41597-025-05438-2). The walkthrough uses `HG008-T` (tumor) and `HG008-N` (normal) PacBio HiFi and ONT-UL reads from the GIAB FTP, together with a Verkko diploid assembly of HG008-N released by the same project. See [References](#references) at the bottom of this page for the full citations.

The walkthrough assumes that:

- The host prerequisites are installed (Snakemake 7.x, Apptainer / Singularity; cookiecutter for clusters) — see [Usage.md](./Usage.md#installation). Cloning the repository and pulling the images is covered in [step 0](#_0-clone-prcgap-and-pull-the-container-images) below.
- Apart from step 0 (which clones the repo and `cd`s into it), all commands in this page are executed from `PRCGAP/test/`, which ships with the helper scripts referenced below:
  - `test_configure.sh` — wraps `setup_workflow.py` with every flag wired to the test fixtures.
  - `config/test_samples.tsv` — pre-authored sample sheet for the HG008 chr20 pair.
  - `resources/scripts/download_data.sh` — fetches the reads and the matched HG008N haplotype assemblies.
  - `resources/scripts/download_reference.sh` — fetches the CHM13 and GRCh38 reference genomes.
  - `resources/scripts/download_annotation.sh` — fetches the external annotation resources (CMRG, gnomAD, GENCODE/MANE).
  - `resources/scripts/README.md` — full per-script inventory, source URLs, and output paths.

> **Required tools on `PATH`.** The download / preparation scripts in steps 1–3 rely on a small set of command-line tools being resolvable from the shell:
>
> | Tool | Used by | Purpose |
> |---|---|---|
> | `python3` | `download_annotation.sh` (and the helpers it invokes) | Filtering CMRG / GENCODE tables |
> | `wget` | `download_data.sh`, `download_reference.sh`, `download_annotation.sh` | Fetching reads, references, and annotation resources |
> | `samtools` | `download_data.sh`, `download_reference.sh` | `view -F 2308` for chr20 slicing, `faidx` for indexing FASTAs and extracting chr20 contigs |
> | `bgzip` | `download_annotation.sh` | Block-gzip compression of BED / VCF outputs |
> | `tabix` | `download_annotation.sh` | Index generation for the bgzipped outputs |
>
> A quick `which python3 wget samtools bgzip tabix` should print a path for each before you start. The pipeline itself runs every tool inside Singularity / Apptainer images, but these helpers run on the host and need the tools available locally.

## 0. Clone PRCGAP and pull the container images

Clone the repository, pull the per-module Singularity / Apptainer images, then move into `test/` — every later step runs from `PRCGAP/test/`, so paths below are written relative to it (no `PRCGAP/` prefix):

```bash
git clone https://github.com/yos-sk/PRCGAP.git
(cd PRCGAP/images && bash pull_images.sh)
cd PRCGAP/test
```

See [Usage.md](./Usage.md#installation) for the full installation details (prerequisites, the image list, and overriding individual images).

## 1. Fetch reads and assemblies

From `PRCGAP/test/`, run the data-download helper (the script `cd`s into its own directory). It pulls the GIAB HG008-T / HG008-N ONT-UL and PacBio HiFi BAMs (CHM13v2.0-aligned), slices each to chr20 with `samtools view -F 2308`, and fetches the matched Verkko 2.2 hap1 / hap2 assemblies for the normal sample (extracting `haplotype1-0000020` and `haplotype2-0000110`, the chr20 contigs):

> **Before you download** — make sure `samtools`, `bgzip`, and `tabix` are all on your `PATH`. The download helpers call `samtools` here to slice the BAMs and index the FASTAs, and `bgzip` / `tabix` in [step 3](#_3-prepare-annotation-files) to compress and index the annotation BED / VCF outputs; any of them missing will make a helper fail partway through. Confirm with `which samtools bgzip tabix` before running.

```bash
(cd resources/scripts && bash download_data.sh)
```

After it completes:

```
test/resources/
├── reads/
│   ├── ont/
│   │   ├── HG008T.chr20.ont.bam
│   │   └── HG008N.chr20.ont.bam
│   └── hifi/
│       ├── HG008T.chr20.hifi.bam
│       └── HG008N.chr20.hifi.bam
└── asm/
    ├── HG008N.hap1.fa{,.fai}        # full assembly (kept so faidx can resolve the chr20 contig)
    ├── HG008N.hap2.fa{,.fai}
    ├── HG008N.hap1.chr20.fa
    └── HG008N.hap2.chr20.fa
```

> **Note** — both the tumor and the normal rows of the sample sheet use the **same** haplotype assemblies (built from the matched normal); this is the standard PRCGAP convention for tumor / normal pairs.

## 2. Fetch reference genomes

PRCGAP needs a base reference in addition to the personalized assembly (CHM13 for the primary coordinate system, GRCh38 for INDEL liftover via transanno). Run the reference-download helper from the same directory:

```bash
(cd resources/scripts && bash download_reference.sh)
```

Outputs:

```
test/resources/reference/
├── chm13v2.0_maskedY_rCRS.fa{,.fai}   # T2T-CHM13 v2.0 (masked Y + rCRS), Human Pangenomics S3
└── GRCh38.d1.vd1.fa{,.fai}            # GRCh38.d1.vd1, GDC
```

## 3. Prepare annotation files

PRCGAP consumes two groups of annotation resources, with different provenance:

### 3a. Haplotype-derived annotations (pre-built, shipped with the repo)

DNA-NN satellites, RepeatMasker (simple repeats, LINE1, full RMSK), Liftoff GTF / GFF, CenSat, SegDup, per-haplotype misassembly tracks, and the liftover chains to GRCh38 / CHM13 — these are all derived from the diploid assembly itself, **not** generated by PRCGAP. For this walkthrough the pre-built chr20 versions are distributed alongside the PRCGAP repository, so they are already present under `test/resources/annotation/` and no action is required from you. The filename scheme matches what `test_configure.sh` expects (`HG008N.<category>.<bed|gtf|gff>.gz`, plus `HG008N.to_{grch38,chm13}.chain`). See [Preparation.md](./Preparation.md) for the upstream steps used to generate these tracks, if you want to derive equivalents for your own samples.

### 3b. External annotations (downloaded)

CMRG gene list, gnomAD v4.1 SV and SNV/INDEL sites, and the GENCODE v46 / MANE v1.3 chr20 transcript BED:

```bash
(cd resources/scripts && bash download_annotation.sh)
```

This emits `cmrg_genes.list`, `gnomad.v4.1.sv.sites.bed.gz{,.tbi}`, `gnomad.genomes.v4.1.sites.chr20.vcf.bgz{,.tbi}`, and `gencode.v46.basic.annotation.chr20.mane.transcript.bed.gz` under `test/resources/annotation/`. The Python helpers `extract_cmrg_gene.py` and `proc_gencode_bed_mane_chr20.py` live next to the script and are invoked automatically.

### 3c. Manual: Cancer Gene Census

The Cancer Gene Census requires a COSMIC account and is **not** downloaded by the helper scripts. After registering at <https://cancer.sanger.ac.uk/cosmic/download/cosmic/v104/cancergenecensus>, place the TSV at:

```
test/resources/annotation/cancer_gene_census.tsv
```

See `test/resources/scripts/README.md` for the full per-file source / step table.

## 4. (Optional) Author a Snakemake profile for HPC users with `cookiecutter`

This section is only for UGE / SLURM / PBS clusters. On a single workstation you can **skip it entirely** and run locally. If you do submit to a scheduler, scaffold a Snakemake profile here, then hand it to `test_configure.sh` in [step 6](#_6-generate-config-yaml-and-run-test-sh) via `--profile`. The full walkthrough (template choice, the 17 interactive prompts, post-generation editing for Lustre + Singularity sites) is in [Usage.md](./Usage.md#optional-but-recommended-author-a-cluster-profile-with-cookiecutter):

```bash
template="gh:Snakemake-Profiles/slurm"     # or gh:Snakemake-Profiles/sge
cookiecutter --output-dir profile $template

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

After scaffolding, pin each job's cores to the scheduler allocation by overwriting the generated jobscript — by default it launches the in-container Snakemake with `--cores all`, which grabs every core on the node instead of the `--cpus-per-task` you requested. Re-apply this after every profile regeneration, since cookiecutter overwrites the file:

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

(For SGE/UGE use the same body but read the allocation from `$NSLOTS` and write it to `profile/sge/sge-jobscript.sh`.) With the profile written under e.g. `profile/slurm/`, add `--profile` when you run `test_configure.sh` in [step 6](#_6-generate-config-yaml-and-run-test-sh):


## 5. Sample sheet

The pre-authored sample sheet ships at `test/config/test_samples.tsv` and looks like:

```
sample	type	ont	hifi	assembly_hap1	assembly_hap2
HG008T	tumor	../resources/reads/ont/HG008T.chr20.ont.bam	../resources/reads/hifi/HG008T.chr20.hifi.bam	../resources/asm/HG008N.hap1.chr20.fa	../resources/asm/HG008N.hap2.chr20.fa
HG008N	normal	../resources/reads/ont/HG008N.chr20.ont.bam	../resources/reads/hifi/HG008N.chr20.hifi.bam	../resources/asm/HG008N.hap1.chr20.fa	../resources/asm/HG008N.hap2.chr20.fa
```

Columns are tab-separated; paths are written relative to the sample sheet's directory (`test/config/`). See [Usage.md](./Usage.md#sample-sheet) for the full column reference and notes on multi-file inputs.

You do not need to edit this file for the walkthrough, but it can equally be regenerated with the bundled `set_sample_sheet.py` helper (see [Usage.md](./Usage.md#sample-sheet)). Run it from `test/config/` so the relative paths resolve, and pass `--no-absolutize` to keep them relative like the shipped version:

```bash
(cd config && python3 ../../set_sample_sheet.py \
    --tumor  HG008T --tumor-ont  ../resources/reads/ont/HG008T.chr20.ont.bam   --tumor-hifi  ../resources/reads/hifi/HG008T.chr20.hifi.bam \
    --normal HG008N --normal-ont ../resources/reads/ont/HG008N.chr20.ont.bam   --normal-hifi ../resources/reads/hifi/HG008N.chr20.hifi.bam \
    --assembly-hap1 ../resources/asm/HG008N.hap1.chr20.fa --assembly-hap2 ../resources/asm/HG008N.hap2.chr20.fa \
    --no-absolutize --force \
    -o test_samples.tsv)
```

(Drop `--no-absolutize` to write absolute paths instead, which is the safer choice if you will run the workflow from a different directory.)

## 6. Generate `config.yaml` and `run_test.sh`

`test_configure.sh` is a thin wrapper around `setup_workflow.py` that points every annotation, reference, image, and resource flag at the files produced by the preceding steps. Run it from `PRCGAP/test/`:

```bash
bash test_configure.sh
```

> **HPC users** — if you set up a Snakemake profile with cookiecutter in the [optional section above](#_4-optional-author-a-snakemake-profile-for-hpc-users-with-cookiecutter), add `--profile profile/slurm` (the path you scaffolded) to the `setup_workflow.py` call inside `test_configure.sh` before running it, so the generated `run_test.sh` submits jobs through the scheduler. On a single workstation, leave it as-is to run locally.

The script writes:

- `test/config/test_config.yaml` — the resolved workflow config.
- `test/run_test.sh` — the runner script.

**Edit `--singularity-bind` to match your environment** before running — list every filesystem root the workflow touches (reads, references, annotations, images, and the output directory). See [Usage.md](./Usage.md#singularity-bind-comma-separated-paths--local-run-bind-mounts) for guidance. The script also pins `--sex female` (matching HG008's donor sex) and a default per-rule thread / memory profile; both can be adjusted by editing the script.

To attach or detach individual variant-annotation resources, comment / uncomment the corresponding flag inside `test_configure.sh` — every flag listed in [Usage.md](./Usage.md#variant-annotation-resource-flags-optional) is optional, so removing a line simply skips that annotation column.

## 7. Run the workflow

```bash
bash run_test.sh
```

On an HPC cluster (jobs submitted through a Snakemake profile), the full chr20 walkthrough takes roughly **1.5 hours** end-to-end. Wall-clock time varies with scheduler queueing and the per-rule resources you allocate; a single workstation will be slower.

Outputs land under `test/HG008/` as configured by `--output-dir` in `test_configure.sh`. For the full output layout (per-module subdirectories, callset filenames, log paths) see [Workflow.md](./Workflow.md#output-layout).

## References

1. **NIST Cancer Genome in a Bottle program.** National Institute of Standards and Technology. <https://www.nist.gov/programs-projects/cancer-genome-bottle>
2. McDaniel, J. H. *et al.* Development and extensive sequencing of a broadly-consented Genome in a Bottle matched tumor-normal pair. *Scientific Data* **12**, 1195 (2025). <https://doi.org/10.1038/s41597-025-05438-2>

## Related pages

- [Preparation.md](./Preparation.md) — Producing the personalized reference and annotation files
- [Usage.md](./Usage.md) — Sample sheet, `setup_workflow.py`, run options
- [Workflow.md](./Workflow.md) — DAG, rule files, output layout
