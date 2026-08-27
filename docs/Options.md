# Options

A complete reference for `setup_workflow.py`, the single entry point that writes the sample sheet, `config.yaml`, and the runner script. Every table lists the flag, the `config.yaml` key it sets (where there is one), and the default.

`python3 setup_workflow.py --help` prints the same list from the script itself.

::: tip Reading order
[Quick start](./QuickStart.md) shows the minimal invocation; this page is the exhaustive list. Only three flags are truly mandatory: `--samplesheet`, `--chm13-fasta`, and — because the gene annotation is always built — `--grch38-fasta` together with `--grch38-gtf`.
:::

## Required

| Flag | config key | Description |
|------|------------|-------------|
| `--samplesheet PATH` | `samplesheet` | Sample sheet TSV. **Written** when any of the pair options below is given, otherwise **read** as-is. |
| `--chm13-fasta PATH` | `chm13_fasta` | CHM13 reference FASTA. Used by copy number, the INDEL `liftvcf_indel_chm13` lift (transanno `--query`), and chain-file generation. |
| `--grch38-fasta PATH` | `grch38_fasta` | GRCh38 reference FASTA. Liftoff source, transanno `--query` for the GRCh38 INDEL lift, and chain-file target. |
| `--grch38-gtf PATH` | `grch38_gtf` | GRCh38 GTF with `chr*` contig names (plain `.gtf`), lifted onto the assembly by the liftoff rule. Its Ensembl release must match `--mane-summary`. |

`setup_workflow.py` errors out if `--grch38-fasta` or `--grch38-gtf` is missing: the liftoff gene annotation is built on every run.

## Sample sheet: writing it from the command line

Give any of these and the sample sheet is written to `--samplesheet` instead of read from it. `--tumor`, `--normal`, `--assembly-hap1`, and `--assembly-hap2` are then all required; the read flags are optional individually but **each sample needs at least one of ONT / HiFi**.

| Flag | Description |
|------|-------------|
| `--tumor NAME` | Tumor sample name. |
| `--normal NAME` | Normal sample name. |
| `--tumor-hifi PATH` | Tumor HiFi data (BAM or FASTQ.gz). Repeatable, and accepts comma-separated lists. |
| `--tumor-ont PATH` | Tumor ONT data. Repeatable / comma-separated. |
| `--normal-hifi PATH` | Normal HiFi data. Repeatable / comma-separated. |
| `--normal-ont PATH` | Normal ONT data. Repeatable / comma-separated. |
| `--assembly-hap1 FASTA` | Haplotype 1 assembly, shared by both samples of the pair. |
| `--assembly-hap2 FASTA` | Haplotype 2 assembly, shared by both samples of the pair. |
| `--no-check-exists` | Do not verify that the data files exist yet (useful when the data is only visible from the compute nodes). |
| `--no-absolutize` | Keep the data paths as given instead of absolutising them. |

Omit **all** of the above to reuse a sheet you wrote by hand; see [Usage → Sample sheet](./Usage.md#sample-sheet) for the column format.

## Sample-level parameters

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--sex {female,male}` | `sex` | `female` | Drives chrY masking (liftoff reference, chain-file masked references) and sex-chromosome handling on the copy-number plot. |

## In-workflow annotation generation

PRCGAP builds the per-assembly annotation it needs from the assembly plus the CHM13 / GRCh38 references, so a run does not have to import it from [assembly_workflow](https://github.com/yos-sk/assembly_workflow). **All four switches default to on**, and the liftoff gene annotation has no switch — it is always built.

| Flag | config key | Default | Builds | Supersedes |
|------|------------|---------|--------|-----------|
| `--run-dna-brnn` / `--no-run-dna-brnn` | `run_dna_brnn` | on | Per-haplotype centromeric satellite BED (dna-brnn) | `--hap1-satellite`, `--hap2-satellite` |
| `--run-simple-repeat` / `--no-run-simple-repeat` | `run_simple_repeat` | on | Tandem-repeat BED (ULTRA, period ≤ 10) used by `nanomonsv get` | `--simple-repeat` |
| `--run-line1` / `--no-run-line1` | `run_line1` | on | Full-length young LINE-1 BED used by `nanomonsv insert_classify` | `--line1-bed` |
| `--run-chain-files` / `--no-run-chain-files` | `run_chain_files` | on | Assembly → CHM13 / GRCh38 chain files | `--chain-to-chm13`, `--chain-to-grch38` |
| *(always on)* | — | — | Liftoff gene annotation (GFF + GTF) | — |

When a switch is on, the generated file wins over the corresponding path key, which can then be left empty. `--no-run-<step>` turns it off, and you supply that file yourself.

References these steps consume:

| Flag | config key | Required for |
|------|------------|--------------|
| `--grch38-fasta` | `grch38_fasta` | liftoff, chain files (and the GRCh38 INDEL lift) |
| `--grch38-gtf` | `grch38_gtf` | liftoff |
| `--chm13-censat` | `chm13_censat` | chain files (satellite masking) — also the copy-number plot |
| `--grch38-centromeres` | `grch38_centromeres` | chain files (UCSC hg38 `centromeres.txt[.gz]`) |
| `--grch38-exclusions` | `grch38_exclusions` | chain files (GRC exclusion-regions BED) |

`--run-line1` needs no reference flag: `resource/line1/{L1.3,l1_3end,l1_5end}.fa` ship with the workflow and are read from the repo. They are **not tracked** — build them once per clone with `bash resource/scripts/build_line1_resources.sh`, which `resource/scripts/download_reference.sh` also does for you.

| config key | Default | Description |
|------------|---------|-------------|
| `simple_repeat_min_copies` | `4` | Minimum repeat copy number kept when `run_simple_repeat` is on. **Config-only** — edit `config.yaml`; there is no CLI flag. |

## Imported annotation paths

Supply these when the corresponding `--run-*` switch is off, or when you have the file from assembly_workflow.

| Flag | config key | Used by |
|------|------------|---------|
| `--hap1-satellite` | `hap1_satellite` | Copy number — masks the hap1 reference |
| `--hap2-satellite` | `hap2_satellite` | Copy number — masks the hap2 reference |
| `--simple-repeat` | `simple_repeat` | `nanomonsv get` — drops indel-like SVs inside a tandem repeat |
| `--line1-bed` | `line1_bed` | `nanomonsv insert_classify` — transduction source elements |
| `--chain-to-grch38` | `chain_to_grch38` | SV / SNV / INDEL liftover to GRCh38 |
| `--chain-to-chm13` | `chain_to_chm13` | SV / SNV / INDEL liftover to CHM13 |

## Variant-annotation resources (all optional)

Every key here is optional. Leaving one empty skips exactly that annotation column — the DAG still resolves and the run still finishes. See [Preparation](./Preparation.md) for how each is produced.

| Flag | config key | Used by |
|------|------------|---------|
| `--repeat-masker-bed` | `repeat_masker_bed` | SV / SNV / INDEL RepeatMasker overlap |
| `--segdup-bed` | `segdup_bed` | SV / SNV / INDEL segmental-duplication overlap |
| `--censat-bed` | `censat_bed` | SV / SNV / INDEL centromere / satellite-subtype overlap |
| `--misassembly-hap1-bed` | `misassembly_hap1_bed` | SV / SNV / INDEL misassembly overlap (hap1) |
| `--misassembly-hap2-bed` | `misassembly_hap2_bed` | SV / SNV / INDEL misassembly overlap (hap2) |
| `--cancer-gene-census-tsv` | `cancer_gene_census_tsv` | Gene-level cancer annotation (COSMIC CGC TSV) |
| `--cmrg-gene-list` | `cmrg_gene_tsv` | SNV / INDEL CMRG annotation (one HGNC symbol per line) |
| `--mane-summary` | `mane_summary` | Restricts SNV / INDEL gene annotation to each gene's MANE transcript. Without it, every protein-coding transcript over the site is reported. Must be the release matching `--grch38-gtf`. |
| `--gnomad-bed` | `gnomad_bed` | SV gnomAD annotation — requires a GRCh38 chain |
| `--gnomad-vcf` | `gnomad_vcf` | SNV / INDEL gnomAD annotation — requires a GRCh38 chain |

`--gnomad-bed` / `--gnomad-vcf` and the transanno INDEL lift all depend on the GRCh38 chain (`--run-chain-files`, or `--chain-to-grch38`) plus `--grch38-fasta`.

## Point-mutation calling

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--mutation-caller {deepsomatic,clairs,both}` | `mutation_caller` | `deepsomatic` | Which caller(s) to run. `both` runs ClairS and DeepSomatic and cross-checks each against the other during annotation. |
| `--mutation-seqtypes {primary,all}` | `mutation_seqtypes` | `primary` | `primary` calls on one seqtype only (HiFi when both are present); `all` calls on every seqtype shared by tumor and normal. SV and methylation always use every available seqtype. |
| `--clairs-model MODEL` | `clairs_model` | `hifi_sequel2` | ClairS platform model, applied to every seqtype ClairS runs on. One of `hifi_sequel2`, `hifi_revio`, `ont_r10_dorado_sup_5khz_ssrs`, `ont_r10_dorado_sup_4khz`. **Set this for ONT data.** |
| `--caller-solo-contig-min-bp N` | `caller_solo_contig_min_bp` | `1000000` | Contigs at least this long get their own caller chunk / job; shorter ones are bundled into one. |
| `--deepsomatic-postprocess-variants-cpus N` | `deepsomatic_postprocess_variants_cpus` | `1` | Worker count for DeepSomatic's `postprocess_variants`, whose own default is the node's core count and ignores the scheduler allocation. |

### Post-processing pileup

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--pileup-no-baq {true,false}` | `pileup_no_baq` | `true` | Pass `--no-BAQ` to `samtools mpileup`. Skipping BAQ is a large peak-RSS saving on long-read / high-depth data. |
| `--pileup-max-depth N` | `pileup_max_depth` | `0` | `samtools mpileup -d`. `0` keeps the samtools default (8000); set > 0 to cap per-file depth in very high-depth regions. |
| `--pileup-num-chunks N` | `pileup_num_chunks` | `16` | Target maximum number of pileup chunks. Contigs are packed into balanced chunks pileup'd with `samtools mpileup -r`. |

## Structural variants

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--run-nanomonsv-connect` | `run_nanomonsv_connect` | off | Run the optional `nanomonsv connect` step (not used in the paper). |
| `--run-nanomonsv-merge` | `run_nanomonsv_merge` | off | Run the optional HiFi + ONT SV merge (not used in the paper). Only fires when both seqtypes are present. |

## Copy number

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--chm13-censat PATH` | `chm13_censat` | *(empty)* | CHM13 cenSat v2.1 BED (`.gz`). Fills assembly gaps in centromeric regions with reference satellite annotation so the plot renders cleanly across centromeres. **Recommended**, and required by `--run-chain-files`. CHM13 chromosome lengths are derived from `--chm13-fasta` at plot time. |
| `--copynumber-binwidth F` | `copynumber_binwidth` | `0.05` | Bin width for the depth-ratio mode / ploidy estimate. |
| `--copynumber-ploidy-hap1 N` | `copynumber_ploidy_hap1` | *(auto)* | Manual hap1 tumor ploidy override; empty auto-estimates. |
| `--copynumber-ploidy-hap2 N` | `copynumber_ploidy_hap2` | *(auto)* | Manual hap2 tumor ploidy override; empty auto-estimates. |
| `--copynumber-hap1-label TEXT` | `copynumber_hap1_label` | `Haplotype1` | Haplotype 1 label on the plot. |
| `--copynumber-hap2-label TEXT` | `copynumber_hap2_label` | `Haplotype2` | Haplotype 2 label on the plot. |
| `--copynumber-plot-sex-chrom {true,false}` | `copynumber_plot_sex_chrom` | `true` | Force chrX / chrY onto the plot even when absent from the data. Set `false` to show them only when present. |

## Container images

`--images-dir` alone is normally enough: every `<key>.sif` inside it is picked up by name. Override an individual image only when you built it locally.

| Flag | Default | Image contents |
|------|---------|----------------|
| `--images-dir DIR` | `images/` next to `setup_workflow.py` | Directory holding the `.sif` files |
| `--bam-refiner-image` | `<images-dir>/bam_refiner.sif` | Read alignment / BAM refinement |
| `--methylation-image` | `<images-dir>/methylation.sif` | pb-CpG-tools (HiFi), modkit (ONT) |
| `--copynumber-image` | `<images-dir>/copynumber.sif` | Copy-number profiling and plotting |
| `--nanomonsv-image` | `<images-dir>/nanomonsv.sif` | nanomonsv parse / get / insert_classify |
| `--nanomonsv-postprocess-image` | `<images-dir>/nanomonsv_postprocess.sif` | nanomonsv postprocess / connect / merge |
| `--clairs-image` | `<images-dir>/clairs.sif` | ClairS |
| `--deepsomatic-image` | `<images-dir>/deepsomatic.sif` | DeepSomatic |
| `--point-mutation-postprocess-image` | `<images-dir>/point_mutation_postprocess.sif` | Realignment / pileup / haplotyping |
| `--annotation-image` | `<images-dir>/annotation.sif` | pysam, samtools, coordconv, transanno, bgzip/tabix |
| `--dna-nn-image` | `<images-dir>/dna_nn.sif` | dna-brnn — only with `--run-dna-brnn` |
| `--liftoff-image` | `<images-dir>/liftoff.sif` | liftoff, minimap2, gffread |
| `--chain-files-image` | `<images-dir>/chain_files.sif` | minimap2, transanno, chaintools, rustybam, paf2chain — only with `--run-chain-files` |

## Output and runner

| Flag | config key | Default | Description |
|------|------------|---------|-------------|
| `--output-dir DIR` | `output_dir` | `results` | Snakemake working directory (`--directory`); everything in [Output directory layout](./Workflow.md#output-directory-layout) is relative to it. |
| `--output PATH`, `-o` | — | `config/config.yaml` | Where the generated `config.yaml` is written. |
| `--runner PATH` | — | `run_workflow.sh` | Where the generated runner script is written. |
| `--workflow-dir DIR` | — | `workflow/` next to `setup_workflow.py` | Directory containing the `Snakefile`. |
| `--targets T [T ...]` | — | *(full pipeline)* | Bake default Snakemake targets into the runner so it builds only those (e.g. `copynumber/{tumor}/output`). Relative to `--output-dir`. Targets given on the runner's command line still win. |
| `--force`, `-f` | — | off | Overwrite an existing config / runner / sample sheet. |
| `--debug` | `debug` | off | Keep the scratch a successful run otherwise deletes — every `workspace/`, the caller scatter dirs, `bwa_index/`, `copynumber/reference/`, and the per-rule copies of `reference.fa`. |

## Execution

| Flag | Default | Description |
|------|---------|-------------|
| `--profile PATH` | *(local)* | Snakemake profile directory (e.g. `profile/slurm`). Path-valued keys inside `<profile>/config.yaml` are rewritten to absolute paths, because Snakemake resolves them against the working directory rather than the profile directory. Without it the runner executes locally. |
| `--jobs N`, `-j` | `8` | Locally: concurrently running rules. With `--profile`: jobs queued in the cluster at once. |
| `--singularity-bind PATHS` | *(empty)* | Comma-separated host paths bind-mounted into every container, forwarded as `--singularity-args "-B <paths> -e"`. |
| `--runner-preamble LINE` | *(none)* | Shell line emitted in the runner before the snakemake call; repeatable. For site setup the generated script cannot know, e.g. `--runner-preamble 'module load apptainer'`. Emitted above `set -euo pipefail` so module init scripts that read unset variables do not abort the runner. |
| `--driver-time D-HH:MM:SS` | `14-00:00:00` | `#SBATCH --time` written into the runner's header block. |
| `--driver-mem GB` | `8` | Memory written into the runner's header block (`#SBATCH --mem-per-cpu` / `#$ -l s_vmem`). |

Run the generated runner with `bash run_workflow.sh` in every case, local or cluster.

## Per-rule resources

Every rule takes `--<rule>-threads` and `--<rule>-mem-mb`, written into `config.yaml` under `resources.<rule>`. The defaults below are sized for a whole human genome; a single-chromosome test wants far less (see [Example](./Example.md)).

| Rule | Threads | Mem (MB) |
|------|--------:|---------:|
| `dna_brnn` | 8 | 8000 |
| `liftoff_reference` | 1 | 8000 |
| `liftoff` | 8 | 80000 |
| `liftoff_merge` | 1 | 16000 |
| `prepare_mask_regions` | 1 | 10240 |
| `make_chain_files` | 8 | 48000 |
| `chain_files_merge` | 1 | 8000 |
| `line1` | 8 | 16000 |
| `line1_merge` | 1 | 8000 |
| `simple_repeat` | 8 | 32000 |
| `simple_repeat_merge` | 1 | 8000 |
| `bam_refiner_kmer` | 8 | 32000 |
| `bam_refiner` | 8 | 64000 |
| `assembly_bwa_index` | 1 | 16000 |
| `methylation` | 8 | 32000 |
| `copynumber` | 8 | 48000 |
| `copynumber_reference` | 1 | 8000 |
| `copynumber_ref_table` | 8 | 48000 |
| `copynumber_ref_table_final` | 1 | 8000 |
| `copynumber_depth` | 4 | 16000 |
| `copynumber_segment` | 1 | 8000 |
| `copynumber_plot` | 1 | 8000 |
| `nanomonsv_parse` | 8 | 16000 |
| `nanomonsv_get` | 8 | 64000 |
| `nanomonsv_postprocess` | 1 | 8000 |
| `nanomonsv_insert_classify` | 8 | 64000 |
| `nanomonsv_connect` | 1 | 30000 |
| `nanomonsv_merge` | 1 | 30000 |
| `clairs` | 8 | 32000 |
| `clairs_scatter_setup` | 8 | 16000 |
| `clairs_chunks` | 1 | 8000 |
| `clairs_merge` | 1 | 16000 |
| `deepsomatic` | 8 | 32000 |
| `deepsomatic_scatter_setup` | 8 | 16000 |
| `deepsomatic_chunks` | 1 | 8000 |
| `deepsomatic_merge` | 1 | 16000 |
| `clairs_postprocess` | 1 | 32000 |
| `clairs_postprocess_split` | 1 | 32000 |
| `clairs_postprocess_realign` | 8 | 16000 |
| `clairs_postprocess_pileup` | 8 | 32000 |
| `clairs_postprocess_haplotype` | 4 | 64000 |
| `deepsomatic_postprocess` | 1 | 32000 |
| `deepsomatic_postprocess_split` | 1 | 32000 |
| `deepsomatic_postprocess_realign` | 8 | 16000 |
| `deepsomatic_postprocess_pileup` | 8 | 32000 |
| `deepsomatic_postprocess_haplotype` | 4 | 64000 |
| `prep_sv` | 1 | 8000 |
| `coordconv_sv` | 1 | 8000 |
| `annotate_sv` | 1 | 16000 |
| `reclassify_sv` | 1 | 16000 |
| `gff_to_bed` | 1 | 8000 |
| `prep_mut` | 1 | 8000 |
| `coordconv_mut` | 1 | 8000 |
| `annotate_mut` | 1 | 16000 |
| `indel_hap_reference` | 1 | 8000 |
| `mut_vcf_index` | 1 | 8000 |
| `bed2vcf_mut` | 1 | 8000 |
| `liftvcf_mut` | 1 | 16000 |

The flag name is the rule name with underscores replaced by hyphens — `nanomonsv_get` → `--nanomonsv-get-threads` / `--nanomonsv-get-mem-mb`.

The copy-number rules that were split out of a formerly monolithic `copynumber` rule inherit the parent's values when their own flag is left at its default, so an existing invocation that only sets `--copynumber-threads` / `--copynumber-mem-mb` still sizes `copynumber_ref_table`, `copynumber_depth`, `copynumber_segment`, and `copynumber_plot`.

::: warning Caller memory and core binding
`clairs` / `deepsomatic` thread counts double as `--num_shards`, and each shard is a separate TensorFlow process. The memory defaults assume the scheduler **binds a job to its allocated cores**; without that binding the shards size themselves from the host's core count and need considerably more. Re-check before lowering either number.
:::

## See also

- [Quick start](./QuickStart.md) — the minimal invocation
- [Usage](./Usage.md) — installation, sample sheet, cluster profile, bind mounts
- [Workflow](./Workflow.md) — what each rule does and where its output lands
