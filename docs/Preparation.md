# Preparation

PRCGAP runs on a **personalized reference genome** — a diploid de novo assembly of the same individual — together with a set of annotation files keyed to that assembly. Generating these inputs is **not** part of PRCGAP itself.

This page lists the inputs PRCGAP requires and shows representative commands for producing each one. The exact tool versions and parameters can be adjusted to your sample type and infrastructure; consult each tool's documentation for the full option list.

## Required inputs

| Input | File | Used by PRCGAP as |
|-------|------|-------------------|
| Phased haplotype assemblies | `{sample}.hap1.fa`, `{sample}.hap2.fa` | `samplesheet.tsv` columns `assembly_hap1` / `assembly_hap2` |
| Centromeric satellite BED (per hap) | `{sample}.hap{1,2}_dna-brnn.bed.gz` | `config.yaml` `hap1_satellite` / `hap2_satellite` |
| Simple repeat BED | `{sample}.simple_repeats.bed.gz` | `config.yaml` `simple_repeat` |
| LINE1 BED | `{sample}.LINE1.bed.gz` | `config.yaml` `line1_bed` |
| Lifted gene annotation GTF | `{sample}.liftoff.gtf.gz` | `config.yaml` `gtf_file` |
| Sample sex | `male` / `female` | `config.yaml` `sex` |
| Base reference FASTA | `CHM13.fa` (or equivalent) | `setup_workflow.py --reference` |

## 1. De novo assembly

Generate phased haplotype assemblies from the **normal** sample long read sequencing data. 

### Option A — Hifiasm (HiFi + ONT-UL, with optional Hi-C or trio)

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
awk '/^S/{print ">"$2"\n"$3}' {sample}.asm.hic.hap1.p_ctg.gfa \
    > {sample}.hap1.fa
awk '/^S/{print ">"$2"\n"$3}' {sample}.asm.hic.hap2.p_ctg.gfa \
    > {sample}.hap2.fa
```

For more details on trio mode, please see [hifiasm](https://github.com/chhylp123/hifiasm) repository.

### Option B — Verkko (HiFi + ONT-UL, with optional Hi-C / Pore-C / trio)

```bash
verkko \
    -d {sample}.verkko \
    --hifi {sample}.hifi.fq.gz \
    --nano {sample}.ont-ul.fq.gz \
    --hic1 {sample}.hic_R1.fq.gz \
    --hic2 {sample}.hic_R2.fq.gz 

# Outputs: {sample}.verkko/assembly.haplotype1.fasta
#          {sample}.verkko/assembly.haplotype2.fasta
cp {sample}.verkko/assembly.haplotype1.fasta {sample}.hap1.fa
cp {sample}.verkko/assembly.haplotype2.fasta {sample}.hap2.fa
```

For more details on Pore-C/trio mode, please see [verkko](https://github.com/marbl/verkko) repository.

## 2. Gene annotation — Liftoff

Transfer gene annotations from GRCh38 (GTF file) onto each haplotype assembly, then concatenate and bgzip:

```bash
# Per haplotype
for hap in hap1 hap2; do
    liftoff \
        -p {threads} \
        -g GTF_file \
        -o {sample}.${hap}.liftoff.gff \
        -u {sample}.${hap}.unmapped.txt \
        {sample}.${hap}.fa GRCh38.fa
done

# Combine and compress
cat {sample}.hap1.liftoff.gff {sample}.hap2.liftoff.gff |\
    grep -v "#" |\
    sort -k1,1 -k4,4n -k5,5n -t$'\t' |\
    bgzip -f -c > {sample}.liftoff.gff.gz
tabix -p gff {sample}.liftoff.gff.gz

zcat {sample}.liftoff.gff.gz | gffread  - -T -o {sample}.liftoff.gtf
gzip {sample}.liftoff.gtf
```

## 3. Repeat annotation — RepeatMasker

Annotate repeats on the combined diploid assembly using [RepeatMakser](https://www.repeatmasker.org) and pull out the two BED files PRCGAP needs (simple repeats and LINE1):

```bash
cat {sample}.hap1.fa {sample}.hap2.fa > {sample}.diploid.fa

RepeatMasker \
    -species human \
    -pa {threads} \
    -dir rmsk_out \
    {sample}.diploid.fa
```

### Simple repeats
```
awk -v OFS='\t' '$11 == /Simple_repeat/' {sample}.rmsk.fa.out \
    | sort -k1,1 -k2,2n | bgzip -c > {sample}.simple_repeats.bed.gz
tabix -p bed {sample}.simple_repeats.bed.gz
```

### LINE1 — write the extraction script, then run it on the RepeatMasker .out
```bash
cat <<'EOF' > extract_LINE1.py
import sys

rmsk_file = sys.argv[1]

with open(rmsk_file, 'r') as f:
    for i, line in enumerate(f):
        if i < 3: continue
        F = line.strip().split()
        if int(F[6]) - int(F[5]) + 1 < 5800: continue
        if F[10] != "LINE/L1": continue
        if not F[9] in ["L1HS", "L1PA2", "L1PA3", "L1PA4", "L1PA5"]: continue
        strand = "-" if F[8] == "C" else "+"
        label = ','.join([F[4], str(int(F[5]) - 1), F[6], strand, F[9]])
        print('\t'.join([F[4], str(int(F[5]) - 1), F[6], label, '0', strand]))
EOF

python3 extract_LINE1.py rmsk_out/{sample}.fa.out \
    | sort -k1,1 -k2,2n \
    | bgzip -c > {sample}.LINE1.bed.gz
tabix -p bed {sample}.LINE1.bed.gz
```

## 5. Centromeric satellite annotation — DNA-NN (per haplotype)

PRCGAP consumes one centromeric satellite BED per haplotype (`hap1_satellite`, `hap2_satellite`). These are produced with [DNA-NN (`dna-brnn`)](https://github.com/lh3/dna-nn), which classifies alpha satellite (HSat1) and HSat2/3 sequences directly from a haplotype FASTA. Run it once per haplotype:

```bash
# attcc-alpha.knm is the pre-trained DNA-NN model
# (download from the dna-nn repository / models/ directory)
for hap in hap1 hap2; do
    dna-brnn \
        -t {threads} \
        -Ai /path/to/attcc-alpha.knm \
        {sample}.${hap}.filt.fa \
        > {sample}.${hap}_dna-brnn.bed

    sort -k1,1 -k2,2n {sample}.${hap}_dna-brnn.bed \
        | bgzip > {sample}.${hap}_dna-brnn.bed.gz
    tabix -p bed {sample}.${hap}_dna-brnn.bed.gz
done
```

`{sample}.hap1_dna-brnn.bed.gz` and `{sample}.hap2_dna-brnn.bed.gz` are what go into `config.yaml` as `hap1_satellite` and `hap2_satellite` respectively.

## 6. (Optional) Variant-annotation resources

PRCGAP's SV and SNV/INDEL annotation modules consume an additional set of resource files. **Every flag is optional**: any missing input simply skips the corresponding annotation column without failing the DAG. The full per-flag table lives in [Usage.md](./Usage.md#variant-annotation-resource-flags-optional); the table below summarises how each resource is typically obtained.

| PRCGAP input | Typical source |
|--------------|----------------|
| `--chain-to-grch38`, `--chain-to-chm13` | Chain files from the personalized assembly to GRCh38 / CHM13 |
| `--segdup-bed` | Sedef / SEDEF segmental-duplication BED, bgzip + `tabix -p bed` |
| `--censat-bed` | CenSat / alphaAnnotation derived centromere/satellite BED on the diploid assembly |
| `--misassembly-hap{1,2}-bed` | Misassembly intervals from QC tools (e.g. NucFreq / VerityMap) on each haplotype |
| `--cancer-gene-census-tsv` | COSMIC Cancer Gene Census TSV |
| `--cmrg-gene-tsv` | CMRG (Challenging Medically Relevant Genes) gene list (https://github.com/usnistgov/cmrg-benchmarkset-manuscript/blob/master/data/gene_coords/unsorted/GRCh38_mrg_full_gene.bed)|
| `--gencode-transcript-bed` | GENCODE transcript BED.gz |
| `--gnomad-bed` | gnomAD SV BED.gz (tabix-indexed, https://storage.googleapis.com/gcp-public-data--gnomad/release/4.1/genome_sv/gnomad.v4.1.sv.sites.bed.gz) |
| `--gnomad-vcf` | gnomAD SNV/INDEL VCF.gz (tabix-indexed, please see https://gnomad.broadinstitute.org/downloads) |
| `--grch38-fasta` | GRCh38 reference FASTA — also used by `setup_workflow.py` as transanno `--query` for INDEL liftover |

`--gnomad-bed`, `--gnomad-vcf`, and the transanno-driven INDEL liftover all require the matching `--chain-to-grch38` (and `--grch38-fasta`) to be supplied.


### 6.1. (Optional) Chain files

PRCGAP's SV / SNV / INDEL annotation can lift every variant back onto GRCh38 and CHM13 to attach the reference coordinate and to cross-reference public resources keyed to those references (notably gnomAD). The liftover is driven by UCSC-style **chain files** that map the personalized haplotype assemblies onto each target reference.

The chain files are produced per haplotype with [minimap2](https://github.com/lh3/minimap2) + [transanno](https://github.com/informationsea/transanno). Run the two commands below once per haplotype (`hap1`, `hap2`) and once per target reference (`GRCh38`, `CHM13`); the four resulting `.chain` files can then be concatenated, or supplied separately as `--chain-to-grch38` / `--chain-to-chm13`:

```bash
# asm5: assembly-to-reference alignment preset (~5% divergence)
minimap2 -cx asm5 -t {threads} {sample}.{hap}.fa ${reference_fasta} \
    > {sample}_{hap}.{reference}.paf

transanno minimap2chain \
    {sample}_{hap}.{reference}.paf \
    --output {sample}_{hap}.{reference}.chain
```

- `{reference_fasta}` is either the GRCh38 FASTA (for `--chain-to-grch38` / `--grch38-fasta`) or the CHM13 FASTA (for `--chain-to-chm13` / `--chm13-fasta`).
- If you generate one chain per haplotype, concatenate them (`cat` of the two `.chain` files is sufficient — chain files are line-oriented) before passing to PRCGAP, since PRCGAP expects a single chain per target reference.
- `--gnomad-bed` and `--gnomad-vcf` depend on `--chain-to-grch38` (and `--grch38-fasta`); leaving the chain empty silently disables those downstream annotations.

### 6.2. (Optional) Segmental duplications

Segmental duplications are large near-identical paralogous segments and a common source of SV / variant-calling artefacts. PRCGAP overlays them onto SV / SNV / INDEL calls so that hits inside known SDs can be filtered or flagged.

[Sedef](https://github.com/vpc-ccg/sedef) detects SDs directly from a haplotype FASTA. Run it once per haplotype, then concatenate, sort, bgzip, and tabix-index to produce the single BED expected by `--segdup-bed`:

```bash
for hap in hap1 hap2; do
    sedef.sh \
        -o sedef_${hap}/ \
        -j {threads} \
        -f \
        {sample}.${hap}.fa
done

# Sedef writes `final.bed` per haplotype; concatenate, sort, bgzip + tabix.
cat sedef_hap1/final.bed sedef_hap2/final.bed \
    | sort -k1,1 -k2,2n \
    | bgzip -c > {sample}.segdup.bed.gz
tabix -p bed {sample}.segdup.bed.gz
```

The same workflow accepts the output of related tools (e.g. [BISER](https://github.com/0xTCG/biser)) — PRCGAP only needs a tabix-indexed BED keyed to the haplotype contigs. See the [sedef repository](https://github.com/vpc-ccg/sedef) for tuning options.

### 6.3. (Optional) Centromere / satellite annotation

The DNA-NN BED produced in §5 (`--hap{1,2}-satellite`) is used **only inside the copynumber module to mask the per-haplotype reference**; the variant-annotation modules do **not** consume it. For SV / SNV / INDEL annotation, PRCGAP instead accepts a **finer-grained centromere / satellite BED on the diploid assembly** (`--censat-bed`), used to mark variants that fall inside specific satellite-array subtypes (HOR / αSat / HSat1A/B / HSat2 / HSat3 …) rather than the coarse `dna-brnn` classes.

This finer annotation is produced with [alphaAnnotation](https://github.com/kmiga/alphaAnnotation), the same pipeline used by the T2T consortium to annotate CHM13's centromeres.

Because alphaAnnotation involves several inter-dependent steps and its exact output layout (filenames, intermediate artefacts, and recommended post-processing) varies across versions, we refer the reader to the upstream documentation rather than reproduce a snapshot here. Please consult the [alphaAnnotation repository](https://github.com/kmiga/alphaAnnotation) for the full installation guide and the most up-to-date run instructions, and follow the post-processing recommended for the version you have installed.

## Hand-off mapping to PRCGAP inputs

Once steps 1–6 are complete, the resulting files map onto PRCGAP entries as follows. Required entries (top block) drive the core variant-calling chain; the variant-annotation block (bottom) is fully optional — any flag left empty simply skips the corresponding column.

| PRCGAP input | Where it is supplied | Source file |
|--------------|----------------------|-------------|
| `assembly_hap1` | `samplesheet.tsv` column | `{sample}.hap1.filt.fa` (step 1) |
| `assembly_hap2` | `samplesheet.tsv` column | `{sample}.hap2.filt.fa` (step 1) |
| `--hap1-satellite` → `hap1_satellite` | `setup_workflow.py` flag → `config.yaml` | `{sample}.hap1_dna-brnn.bed.gz` (step 5) |
| `--hap2-satellite` → `hap2_satellite` | `setup_workflow.py` flag → `config.yaml` | `{sample}.hap2_dna-brnn.bed.gz` (step 5) |
| `--simple-repeat` → `simple_repeat` | `setup_workflow.py` flag → `config.yaml` | `{sample}.simple_repeats.bed.gz` (step 3) |
| `--line1-bed` → `line1_bed` | `setup_workflow.py` flag → `config.yaml` | `{sample}.LINE1.bed.gz` (step 3) |
| `--gtf-file` → `gtf_file` | `setup_workflow.py` flag → `config.yaml` | `{sample}.liftoff.gtf.gz` (step 2) |
| `--sex` → `sex` | `setup_workflow.py` flag → `config.yaml` | Sample metadata |
| **Variant-annotation resources (all optional — step 6)** | | |
| `--gff-file` → `gff_file` | `setup_workflow.py` flag → `config.yaml` | `{sample}.liftoff.gff.gz` (step 2) |
| `--chain-to-grch38` → `chain_to_grch38` | `setup_workflow.py` flag → `config.yaml` | `{sample}.to_grch38.chain` (step 6.1) |
| `--chain-to-chm13` → `chain_to_chm13` | `setup_workflow.py` flag → `config.yaml` | `{sample}.to_chm13.chain` (step 6.1) |
| `--repeat-masker-bed` → `repeat_masker_bed` | `setup_workflow.py` flag → `config.yaml` | RepeatMasker BED.gz (step 3) |
| `--segdup-bed` → `segdup_bed` | `setup_workflow.py` flag → `config.yaml` | Sedef segdup BED.gz (step 6.2) |
| `--censat-bed` → `censat_bed` | `setup_workflow.py` flag → `config.yaml` | CenSat / alphaAnnotation BED.gz (step 6.3) |
| `--misassembly-hap1-bed` → `misassembly_hap1_bed` | `setup_workflow.py` flag → `config.yaml` | hap1 misassembly BED (step 6) |
| `--misassembly-hap2-bed` → `misassembly_hap2_bed` | `setup_workflow.py` flag → `config.yaml` | hap2 misassembly BED (step 6) |
| `--cancer-gene-census-tsv` → `cancer_gene_census_tsv` | `setup_workflow.py` flag → `config.yaml` | COSMIC Cancer Gene Census TSV (step 6) |
| `--cmrg-gene-tsv` → `cmrg_gene_tsv` | `setup_workflow.py` flag → `config.yaml` | CMRG gene list TSV (step 6) |
| `--gencode-transcript-bed` → `gencode_transcript_bed` | `setup_workflow.py` flag → `config.yaml` | GENCODE transcript BED.gz (step 6) |
| `--gnomad-bed` → `gnomad_bed` | `setup_workflow.py` flag → `config.yaml` | gnomAD SV BED.gz (step 6; requires `--chain-to-grch38`) |
| `--gnomad-vcf` → `gnomad_vcf` | `setup_workflow.py` flag → `config.yaml` | gnomAD SNV/INDEL VCF.gz (step 6; requires `--chain-to-grch38`) |
| `--grch38-fasta` → `grch38_fasta` | `setup_workflow.py` flag → `config.yaml` | GRCh38 reference FASTA (step 6; requires `--chain-to-grch38`) |

For tumor / normal pairs, **both samples must use the same haplotype assemblies** (typically those built from the matched normal): the same paths appear in `assembly_hap1` / `assembly_hap2` for the tumor and the normal rows of `samplesheet.tsv`.

## Reference genome

In addition to the personalized assembly, PRCGAP requires a base reference (e.g. T2T-CHM13) for context and coordinate operations. Supply it directly via `setup_workflow.py --reference /path/to/CHM13.fa`. The reference is independent of the per-sample assembly and annotation files above.

## Next step

Once the assembly and annotation files in hand, proceed to [Usage.md](./Usage.md) to author the sample sheet and generate `config.yaml`.
