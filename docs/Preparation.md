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
    gffread {sample}.${hap}.liftoff.gff -T -o {sample}.${hap}.liftoff.gtf
done

# Combine and compress
cat {sample}.hap1.liftoff.gtf {sample}.hap2.liftoff.gtf \
    | sort -k1,1 -k4,4n \
    | bgzip > {sample}.liftoff.gtf.gz
tabix -p gff {sample}.liftoff.gtf.gz
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

## 6. (Optional) Tandem repeats and segmental duplications

Not consumed by PRCGAP directly, but commonly produced alongside the above and useful for downstream interpretation:

- **TRF-mod** — tandem repeat annotation: `trf-mod {sample}.diploid.fa > {sample}.trf-mod.bed`
- **Sedef** — segmental duplications


## Hand-off mapping to PRCGAP inputs

Once steps 1–5 are complete, the resulting files map onto PRCGAP entries as follows.

| PRCGAP input | Where it is supplied | Source file |
|--------------|----------------------|-------------|
| `assembly_hap1` | `samplesheet.tsv` column | `{sample}.hap1.filt.fa` (step 1–2) |
| `assembly_hap2` | `samplesheet.tsv` column | `{sample}.hap2.filt.fa` (step 1–2) |
| `--hap1-satellite` → `hap1_satellite` | `setup_workflow.py` flag → `config.yaml` | `{sample}.hap1_dna-brnn.bed.gz` (step 5) |
| `--hap2-satellite` → `hap2_satellite` | `setup_workflow.py` flag → `config.yaml` | `{sample}.hap2_dna-brnn.bed.gz` (step 5) |
| `--simple-repeat` → `simple_repeat` | `setup_workflow.py` flag → `config.yaml` | `{sample}.simple_repeats.bed.gz` (step 4) |
| `--line1-bed` → `line1_bed` | `setup_workflow.py` flag → `config.yaml` | `{sample}.LINE1.bed.gz` (step 4) |
| `--gtf-file` → `gtf_file` | `setup_workflow.py` flag → `config.yaml` | `{sample}.liftoff.gtf.gz` (step 3) |
| `--sex` → `sex` | `setup_workflow.py` flag → `config.yaml` | Sample metadata |

For tumor / normal pairs, **both samples must use the same haplotype assemblies** (typically those built from the matched normal): the same paths appear in `assembly_hap1` / `assembly_hap2` for the tumor and the normal rows of `samplesheet.tsv`.

## Reference genome

In addition to the personalized assembly, PRCGAP requires a base reference (e.g. T2T-CHM13) for context and coordinate operations. Supply it directly via `setup_workflow.py --reference /path/to/CHM13.fa`. The reference is independent of the per-sample assembly and annotation files above.

## Next step

Once the assembly and annotation files in hand, proceed to [Usage.md](./Usage.md) to author the sample sheet and generate `config.yaml`.
