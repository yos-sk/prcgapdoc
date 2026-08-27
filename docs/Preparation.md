# Preparation

PRCGAP runs on a **personalized reference genome** — a phased diploid de novo assembly of the same individual. That assembly is the one input PRCGAP cannot produce: everything else it needs, it builds itself from the assembly plus the public references fetched by `resource/scripts/download_reference.sh`.

So this page has two halves:

1. **[De novo assembly](#_1-de-novo-assembly-required)** — required. Hifiasm or Verkko on the normal sample's long reads.
2. **[Deeper annotation](#_3-optional-deeper-annotation)** — optional. Four extra annotation tracks that add columns to the SV and SNV/INDEL tables. PRCGAP does not build these, and does not need them: a run without any of them completes and simply omits those columns.

With the assembly in hand you can go straight to [Quick start](./QuickStart.md).

## 1. De novo assembly (required)

Generate phased haplotype assemblies from the **normal** sample's long reads. Either assembler below works; both are also wrapped by the Assembly module of [assembly_workflow](https://github.com/yos-sk/assembly_workflow), which additionally filters and renames contigs.

### Option A: Hifiasm (HiFi + ONT-UL, with optional Hi-C or trio)

```bash
# HiFi + ONT-UL + Hi-C
hifiasm \
    -o {sample}.asm \
    -t {threads} \
    --h1 {sample}.hic_R1.fq.gz \
    --h2 {sample}.hic_R2.fq.gz \
    --ul {sample}.ont-ul.fq.gz \
    {sample}.hifi.fq.gz

# Convert phased contig GFA → FASTA
awk '/^S/{print ">"$2"\n"$3}' {sample}.asm.hic.hap1.p_ctg.gfa > {sample}.hap1.fa
awk '/^S/{print ">"$2"\n"$3}' {sample}.asm.hic.hap2.p_ctg.gfa > {sample}.hap2.fa
```

For trio mode, see the [hifiasm](https://github.com/chhylp123/hifiasm) repository.

### Option B: Verkko (HiFi + ONT-UL, with optional Hi-C / Pore-C / trio)

```bash
verkko \
    -d {sample}.verkko \
    --hifi {sample}.hifi.fq.gz \
    --nano {sample}.ont-ul.fq.gz \
    --hic1 {sample}.hic_R1.fq.gz \
    --hic2 {sample}.hic_R2.fq.gz

cp {sample}.verkko/assembly.haplotype1.fasta {sample}.hap1.fa
cp {sample}.verkko/assembly.haplotype2.fasta {sample}.hap2.fa
```

For Pore-C / trio mode, see the [verkko](https://github.com/marbl/verkko) repository.

The two FASTAs go to `setup_workflow.py` as `--assembly-hap1` / `--assembly-hap2`.

::: warning One assembly per run
For tumor / normal pairs, **both samples use the same haplotype assemblies** — typically those built from the matched normal. `setup_workflow.py` enforces this.
:::

## 2. What PRCGAP builds for itself

Given the assembly and the public references, PRCGAP generates the per-assembly annotation it needs to interpret its own calls. Nothing here has to be prepared in advance:

| Annotation | Switch | Consumed by |
|---|---|---|
| Gene annotation — GFF + GTF on the assembly | *always built* | SV / SNV / INDEL gene annotation, `nanomonsv insert_classify` |
| Centromeric satellite BED, per haplotype | `--run-dna-brnn` (on) | Copy number — masks the per-haplotype reference |
| Assembly → GRCh38 / CHM13 chain files | `--run-chain-files` (on) | SV / SNV / INDEL liftover, gnomAD lookup |
| Full-length young LINE-1 BED | `--run-line1` (on) | `nanomonsv insert_classify` — transduction source elements |
| Tandem-repeat BED | `--run-simple-repeat` (on) | `nanomonsv get` — drops indel-like SVs inside a repeat |

The four switches default to on; see [Workflow → Assembly annotation](./Workflow.md#_0-assembly-annotation) for what each rule does and where its output lands. If you already have one of these files, or want the two pipelines to agree file-for-file, you can import it instead — see [Overriding a built-in step](#_5-overriding-a-built-in-annotation-step).

## 3. Optional: deeper annotation

Four annotation tracks are **not** built in-workflow. Each adds a column to the SV and SNV/INDEL tables; a missing one is filled with the `-` placeholder and the DAG still resolves, so all four are genuinely optional.

| Track | Flag | Adds |
|---|---|---|
| RepeatMasker | `--repeat-masker-bed` | The repeat class each variant falls in |
| Segmental duplications | `--segdup-bed` | Whether a call sits in a known SD — a common artefact source |
| cenSat satellite subtypes | `--censat-bed` | The specific satellite array (HOR / αSat / HSat1A/B / HSat2 / HSat3 …) |
| Per-haplotype misassembly | `--misassembly-hap{1,2}-bed` | Whether a call sits in an interval assembly QC flagged as unreliable |

### Via assembly_workflow

The straightforward way to get all four is the companion pipeline **[assembly_workflow](https://github.com/yos-sk/assembly_workflow)**, whose Annotation and Evaluation modules produce them. Every tool dependency ships as a Singularity/Apptainer image, so the host requirements are the same as PRCGAP's — if you can run PRCGAP you need nothing new.

| PRCGAP flag | assembly_workflow module / output |
|---|---|
| `--repeat-masker-bed` | Annotation → RepeatMasker |
| `--segdup-bed` | Annotation → SEDEF |
| `--censat-bed` | Annotation → CenSat |
| `--misassembly-hap{1,2}-bed` | Evaluation → Flagger / Inspector / NucFlag |

If you already have haplotype assemblies (from [§1](#_1-de-novo-assembly-required) or elsewhere), run only the two modules that matter here — pass the assemblies with `--hap1-assembly` / `--hap2-assembly` and `--run-modules evaluation,annotation`, skipping assembly generation entirely:

```bash
git clone https://github.com/yos-sk/assembly_workflow.git
cd assembly_workflow
(cd images && bash pull_image.sh)

# (Cluster only) scaffold a profile — the same jobscript patch as PRCGAP applies.
cookiecutter --output-dir profile gh:Snakemake-Profiles/slurm   # or .../sge

# References + the CenSat HMM/k-mer database, first time only.
bash download_reference.sh reference
( cd reference && singularity exec ../images/compleasm.sif compleasm download primates --odb odb10 )
( cd workflow/scripts/annotation/censat/db && bash download.sh )

python3 set_sample_sheet.py --samplesheet config/samples.tsv \
    --sample S1 --sex female \
    --run-modules evaluation,annotation --assembler verkko \
    --hap1-assembly /data/S1.hap1.fa --hap2-assembly /data/S1.hap2.fa \
    --hifi /data/S1.hifi.bam

python3 setup_workflow.py \
    --samplesheet config/samples.tsv \
    --output config/config.yaml \
    --runner run_workflow.sh \
    --chm13 reference/chm13v2.0_maskedY_rCRS.fa \
    --grch38 reference/GRCh38.d1.vd1.fa \
    --chm13-satellite reference/chm13v2.0_censat_v2.1.bed \
    --grch38-centromeres reference/centromeres.txt.gz \
    --grch38-exclusions reference/GCA_000001405.15_GRCh38_GRC_exclusions_T2Tv2.bed \
    --grch38-gtf reference/Homo_sapiens.GRCh38.Ensembl.112.chr.format.gtf \
    --compleasm-library reference/mb_downloads \
    --images-dir images \
    --singularity-bind "$HOME" \
    --profile profile/slurm        # omit for local execution

./run_workflow.sh
```

Use `--run-modules all` instead if you want assembly_workflow to build the assembly too, in which case pass reads (`--hifi`, `--ont-ul`, and optionally `--hic-r1` / `--hic-r2`) rather than `--hap{1,2}-assembly`. See the [assembly_workflow README](https://github.com/yos-sk/assembly_workflow/blob/main/README.md) for the full flag list.

### Or tool by tool

The sections below produce the same four files outside either pipeline. Versions and parameters can be adjusted to your sample type and infrastructure; consult each tool's documentation for the full option list.

#### 3.1. RepeatMasker

Run [RepeatMasker](https://www.repeatmasker.org) on the combined diploid assembly and convert the `.out` table to a tabix-indexed BED:

```bash
RepeatMasker \
    -species human \
    -pa {threads} \
    -dir rmsk_out \
    {sample}.{hap}.fa
```

This is expensive — hundreds of core-hours for a diploid human assembly. It is precisely why PRCGAP's LINE-1 and tandem-repeat steps take lighter routes instead of depending on RepeatMasker. Skip `--repeat-masker-bed` if you do not need the general repeat column.

#### 3.2. Segmental duplications

[Sedef](https://github.com/vpc-ccg/sedef) detects SDs directly from a haplotype FASTA. Run it per haplotype, then concatenate, sort, bgzip, and tabix-index into the single BED `--segdup-bed` expects:

```bash
for hap in hap1 hap2; do
    sedef.sh -o sedef_${hap}/ -j {threads} -f {sample}.${hap}.fa
done

cat sedef_hap1/final.bed sedef_hap2/final.bed \
    | sort -k1,1 -k2,2n | bgzip -c > {sample}.segdup.bed.gz
tabix -p bed {sample}.segdup.bed.gz
```

The output of related tools (e.g. [BISER](https://github.com/0xTCG/biser)) works equally well — PRCGAP only needs a tabix-indexed BED keyed to the haplotype contigs.

#### 3.3. Centromere / satellite subtypes

`--censat-bed` is a **finer-grained** centromere / satellite annotation on the diploid assembly, marking variants inside specific satellite-array subtypes rather than the coarse `dna-brnn` classes. The two are not interchangeable: the dna-brnn BED PRCGAP builds is used only for copy-number masking, and `--censat-bed` only by variant annotation.

It is produced with [alphaAnnotation](https://github.com/kmiga/alphaAnnotation), the pipeline the T2T consortium used to annotate CHM13's centromeres. Because it involves several inter-dependent steps whose output layout varies across versions, follow the [alphaAnnotation repository](https://github.com/kmiga/alphaAnnotation) for installation and the post-processing recommended for the version you have.

#### 3.4. Misassembly tracks

Produce these with a misassembly detector run per haplotype — [Flagger](https://github.com/mobinasri/flagger), [Inspector](https://github.com/Maggi-Chen/Inspector), [NucFlag](https://github.com/logsdon-lab/NucFlag), NucFreq, or VerityMap. assembly_workflow's Evaluation module wraps the first three. The result is a per-haplotype BED of intervals to treat as unreliable, passed as `--misassembly-hap1-bed` / `--misassembly-hap2-bed`.

## 4. Public databases

Four more optional annotations come from public resources rather than from your assembly:

| Flag | Source |
|------|--------|
| `--cancer-gene-census-tsv` | [COSMIC Cancer Gene Census](https://cancer.sanger.ac.uk/cosmic/download/cosmic/v104/cancergenecensus) TSV — requires a COSMIC account |
| `--cmrg-gene-list` | CMRG (Challenging Medically Relevant Genes) list, one HGNC symbol per line — derived from [`GRCh38_mrg_full_gene.bed`](https://github.com/usnistgov/cmrg-benchmarkset-manuscript/blob/master/data/gene_coords/unsorted/GRCh38_mrg_full_gene.bed) |
| `--gnomad-bed` | [gnomAD v4.1 SV sites BED.gz](https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/genome_sv/gnomad.v4.1.sv.sites.bed.gz), tabix-indexed |
| `--gnomad-vcf` | gnomAD SNV/INDEL sites VCF.gz, tabix-indexed — see [gnomAD downloads](https://gnomad.broadinstitute.org/downloads) |

Both gnomAD resources need a GRCh38 chain (built by `--run-chain-files`, or supplied via `--chain-to-grch38`) plus `--grch38-fasta`: the lift to GRCh38 is what makes the lookup possible.

## 5. Overriding a built-in annotation step

Rarely needed: the steps in [§2](#_2-what-prcgap-builds-for-itself) run inside the workflow, so there is nothing to prepare. If you already have one of these files — from assembly_workflow, or because you want the two pipelines to agree file-for-file — pass `--no-run-<step>` together with the corresponding path flag and the imported file is used instead.

| Step | Turn off with | Import with |
|---|---|---|
| Centromeric satellites | `--no-run-dna-brnn` | `--hap1-satellite`, `--hap2-satellite` |
| Chain files | `--no-run-chain-files` | `--chain-to-grch38`, `--chain-to-chm13` |
| LINE-1 | `--no-run-line1` | `--line1-bed` |
| Tandem repeats | `--no-run-simple-repeat` | `--simple-repeat` |

The gene annotation has no switch — liftoff always runs.

## 6. Hand-off mapping to PRCGAP flags

| PRCGAP flag | config key | Source |
|--------------|-----------|--------|
| `--assembly-hap1` / `--assembly-hap2` | sample-sheet columns | §1 — **required** |
| **Deeper annotation, all optional** | | |
| `--repeat-masker-bed` | `repeat_masker_bed` | §3.1 |
| `--segdup-bed` | `segdup_bed` | §3.2 |
| `--censat-bed` | `censat_bed` | §3.3 |
| `--misassembly-hap1-bed` / `--misassembly-hap2-bed` | `misassembly_hap{1,2}_bed` | §3.4 |
| `--cancer-gene-census-tsv` | `cancer_gene_census_tsv` | §4 |
| `--cmrg-gene-list` | `cmrg_gene_tsv` | §4 |
| `--gnomad-bed` | `gnomad_bed` | §4 (needs a GRCh38 chain) |
| `--gnomad-vcf` | `gnomad_vcf` | §4 (needs a GRCh38 chain) |
| **Only when overriding a built-in step** | | |
| `--hap1-satellite` / `--hap2-satellite` | `hap1_satellite` / `hap2_satellite` | §5 (with `--no-run-dna-brnn`) |
| `--chain-to-grch38` / `--chain-to-chm13` | `chain_to_grch38` / `chain_to_chm13` | §5 (with `--no-run-chain-files`) |
| `--line1-bed` | `line1_bed` | §5 (with `--no-run-line1`) |
| `--simple-repeat` | `simple_repeat` | §5 (with `--no-run-simple-repeat`) |

The public references themselves (`--chm13-fasta`, `--grch38-fasta`, `--grch38-gtf`, `--chm13-censat`, `--grch38-centromeres`, `--grch38-exclusions`, `--mane-summary`) are fetched once by `resource/scripts/download_reference.sh` — see [Quick start → step 3](./QuickStart.md#_3-fetch-the-references-once-per-installation).

## Next step

With the assembly ready, go to [Quick start](./QuickStart.md) to configure and launch the run. [Options](./Options.md) has the full flag reference.
