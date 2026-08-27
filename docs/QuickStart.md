# Quick start

PRCGAP needs **three things** to run: long reads for a tumor / normal pair, a phased diploid assembly of the normal, and a one-time set of public reference files. Everything else — the per-assembly annotation the pipeline reasons about its own calls with — PRCGAP builds itself.

```
reads (bam / fastq.gz)     ─┐
assembly hap1 / hap2 FASTA  ├─► setup_workflow.py ─► run_workflow.sh ─► callsets
public references          ─┘
```

This page is the shortest path from a clone to a finished run. If you want the richer annotation set (segmental duplications, cenSat subtypes, RepeatMasker, misassembly tracks), run the companion [assembly_workflow](https://github.com/yos-sk/assembly_workflow) pipeline first and pass its outputs in — see [Preparation](./Preparation.md). That is strictly additive: the run below works without any of it.

## What you need

| Input | Notes |
|-------|-------|
| Tumor reads | PacBio HiFi and/or ONT, bam or fastq.gz. **Either sequencing type alone is enough** — see [HiFi-only / ONT-only](#hifi-only-ont-only-runs). |
| Normal reads | Same seqtypes as the tumor (a seqtype is analysed only when both samples have it). |
| `{normal}.hap1.fa`, `{normal}.hap2.fa` | Phased diploid assembly of the **normal**, from Hifiasm / Verkko / assembly_workflow. Tumor and normal are both aligned to it. |
| Sample sex | `male` / `female` — drives chrY masking and the copy-number plot. |
| Public references | Fetched once by `resource/scripts/download_reference.sh` (below). |

::: tip One pair per run
A run is one tumor / normal pair on one assembly, because the per-assembly annotation in `config.yaml` is global. A second pair gets its own config, sample sheet, and `--output-dir`.
:::

## 1. Prerequisites

Only three host-side tools; every analysis step runs inside a container.

```bash
mamba create -n PRCGAP -c conda-forge -c bioconda "snakemake>=7,<8" pyyaml
mamba install -n PRCGAP -c conda-forge apptainer      # skip if the host provides it
mamba install -n PRCGAP -c conda-forge cookiecutter   # only for a cluster profile
mamba activate PRCGAP
```

::: warning Snakemake >= 8 is not supported
PRCGAP is validated against **7.32.4**. Snakemake 8 renamed the container and profile CLI (`--sdm` for `--use-singularity`, new profile format). Pin the version.
:::

## 2. Clone and pull the images

```bash
git clone https://github.com/yos-sk/PRCGAP.git
cd PRCGAP
(cd images && bash pull_images.sh)
```

This is the slow part — roughly **30 minutes**, dominated by pulling and converting twelve container images. See [Usage → Container images](./Usage.md#container-images) for the list.

## 3. Fetch the references (once per installation)

```bash
bash resource/scripts/download_reference.sh
```

Writes into `resource/reference/` and additionally builds `resource/line1/*.fa`, the LINE-1 query and subunit models the in-workflow LINE-1 step reads:

| File | Passed as | Needed for |
|------|-----------|------------|
| `chm13v2.0_maskedY_rCRS.fa` | `--chm13-fasta` | always (copy number, INDEL liftover, chain files) |
| `GRCh38.d1.vd1.fa` | `--grch38-fasta` | always (liftoff source, INDEL liftover, chain files) |
| `Homo_sapiens.GRCh38.Ensembl.112.chr.format.gtf` | `--grch38-gtf` | always (liftoff gene annotation) |
| `chm13v2.0_censat_v2.1.bed.gz` | `--chm13-censat` | chain files + copy-number plot |
| `centromeres.txt.gz` | `--grch38-centromeres` | chain files |
| `GCA_000001405.15_GRCh38_GRC_exclusions_T2Tv2.bed` | `--grch38-exclusions` | chain files |
| `MANE.GRCh38.v1.3.summary.txt.gz` | `--mane-summary` | SNV / INDEL gene annotation |
| `resource/line1/{L1.3,l1_3end,l1_5end}.fa` | — (read from the repo) | LINE-1 annotation |

Needs `samtools`, `bgzip`, and `tabix` on `PATH`, plus `images/nanomonsv.sif` for the LINE-1 models.

## 4. (Cluster only) scaffold a Snakemake profile

Skip this on a single workstation. On SLURM or SGE/UGE, generate a profile with cookiecutter and hand it to `setup_workflow.py --profile`:

```bash
cookiecutter --output-dir profile gh:Snakemake-Profiles/slurm   # or .../sge
```

The full walkthrough — the interactive prompts, and the jobscript patch that pins each job's `--cores` to its allocation — is in [Usage → cluster profile](./Usage.md#optional-but-recommended-author-a-cluster-profile-with-cookiecutter). **Apply the jobscript patch**; without it every job grabs every core on its node.

## 5. Configure

`setup_workflow.py` writes the sample sheet, a fully-resolved `config.yaml`, and a ready-to-run `run_workflow.sh`. The `--tumor` / `--normal` options write the sheet for you, so there is no separate sheet-authoring step.

```bash
python3 setup_workflow.py \
    --samplesheet config/samples.tsv \
    --tumor  TUMOR  --tumor-hifi  /data/tumor.hifi.bam  --tumor-ont  /data/tumor.ont.bam \
    --normal NORMAL --normal-hifi /data/normal.hifi.bam --normal-ont /data/normal.ont.bam \
    --assembly-hap1 /data/NORMAL.hap1.fa \
    --assembly-hap2 /data/NORMAL.hap2.fa \
    --sex female \
    --chm13-fasta        resource/reference/chm13v2.0_maskedY_rCRS.fa \
    --grch38-fasta       resource/reference/GRCh38.d1.vd1.fa \
    --grch38-gtf         resource/reference/Homo_sapiens.GRCh38.Ensembl.112.chr.format.gtf \
    --chm13-censat       resource/reference/chm13v2.0_censat_v2.1.bed.gz \
    --grch38-centromeres resource/reference/centromeres.txt.gz \
    --grch38-exclusions  resource/reference/GCA_000001405.15_GRCh38_GRC_exclusions_T2Tv2.bed \
    --mane-summary       resource/reference/MANE.GRCh38.v1.3.summary.txt.gz \
    --output-dir     /path/to/output \
    --output         config/config.yaml \
    --runner         run_workflow.sh \
    --singularity-bind "$HOME" \
    --profile profile/slurm      # omit for local execution
#   add --force (-f) to overwrite an existing config / runner / sheet
```

That is the whole minimal invocation. Note what is **not** in it: no satellite BED, no LINE-1 BED, no tandem-repeat BED, no gene GTF, no chain files. The four `--run-*` switches that build those default to **on**, and the gene annotation is always built.

```
--run-dna-brnn        per-haplotype centromeric satellite BED   (default on)
--run-simple-repeat   tandem-repeat BED for nanomonsv get       (default on)
--run-line1           full-length young LINE-1 BED              (default on)
--run-chain-files     assembly → CHM13 / GRCh38 chain files     (default on)
(always)              liftoff gene annotation (GFF + GTF)
```

Pass `--no-run-<step>` to turn one off and import that file instead via its path flag (`--hap1-satellite`, `--simple-repeat`, `--line1-bed`, `--chain-to-grch38` / `--chain-to-chm13`).

::: warning Bind mounts
`--singularity-bind` must cover every filesystem root the run touches: reads, assembly, references, `images/`, and `--output-dir`. Paths not bound are invisible inside the container. If any input is a symlink, bind both the link's directory and its target. See [Usage → `--singularity-bind`](./Usage.md#bind-mounts).
:::

## 6. Run

```bash
bash run_workflow.sh
```

## HiFi-only / ONT-only runs

Omit the flags for the seqtype you do not have; the sample sheet's `ont` and `hifi` columns are both optional and each sample only needs one of them.

```bash
# HiFi-only pair
python3 setup_workflow.py ... \
    --tumor T --tumor-hifi t.hifi.bam --normal N --normal-hifi n.hifi.bam

# ONT-only pair
python3 setup_workflow.py ... \
    --tumor T --tumor-ont t.ont.bam --normal N --normal-ont n.ont.bam \
    --clairs-model ont_r10_dorado_sup_5khz_ssrs      # only if --mutation-caller clairs/both
```

What changes:

| | HiFi + ONT | HiFi-only | ONT-only |
|---|---|---|---|
| BAM refinement, methylation | both seqtypes | HiFi | ONT |
| Nanomonsv + SV annotation | both, independently | HiFi | ONT |
| Point mutations | HiFi (see below) | HiFi | ONT |
| Copy number | HiFi | HiFi | ONT |

- A seqtype is analysed only when **both** the tumor and its paired normal carry it.
- Point-mutation calling defaults to `--mutation-seqtypes primary` — one seqtype, HiFi when both are present. Pass `--mutation-seqtypes all` to call on every shared seqtype.
- Copy number always uses the primary shared seqtype.
- The optional `--run-nanomonsv-merge` step (HiFi+ONT SV merge) is only meaningful when both seqtypes are present and is skipped otherwise.
- With `--mutation-caller clairs` or `both`, set `--clairs-model` to match your data; the default `hifi_sequel2` is a HiFi model.

## Where the results land

Under `--output-dir`. The leaves you most likely want:

| Result | Path |
|--------|------|
| Copy-number plot | `copynumber/{tumor}/output/{tumor}.copynumber.png` |
| Copy-number segments | `copynumber/{tumor}/output/{tumor}.hap{1,2}.cbs.txt` |
| Annotated SVs | `annotate_sv/{tumor}/{seqtype}/{tumor}.PRCGAP.nanomonsv_results.reclassified.txt` |
| Annotated SNVs | `annotate_snv/{tumor}/{tool}/{seqtype}/{tumor}.{tool}.snv.annotated.txt` |
| Annotated INDELs | `annotate_indel/{tumor}/{tool}/{seqtype}/{tumor}.{tool}.indel.annotated.txt` |
| Methylation | `methylation/{sample}/{seqtype}/output/` |

The full tree is in [Workflow → Output directory layout](./Workflow.md#output-directory-layout).

## Next steps

- [Usage](./Usage.md) — installation detail, sample-sheet columns, cluster profiles, bind mounts
- [Options](./Options.md) — every `setup_workflow.py` flag and `config.yaml` key
- [Preparation](./Preparation.md) — the optional deeper annotation set, via assembly_workflow
- [Example](./Example.md) — the HG008 chr20 walkthrough, with the files a finished run produces
