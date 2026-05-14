# Workflow

This page describes how PRCGAP is structured internally: the rule files, the dependencies between modules, and the output directory layout.

## DAG

To generate the full directed acyclic graph (DAG) for a given configuration:

```bash
snakemake \
    --snakefile /path/to/PRCGAP/workflow/snakefile \
    --configfile /path/to/config.yaml \
    --directory /path/to/output \
    --dag | dot -Tsvg > prcgap_dag.svg
```

Use `--rulegraph` instead of `--dag` for a higher-level, rule-only view that does not enumerate per-sample / per-chromosome jobs:

```bash
snakemake ... --rulegraph | dot -Tsvg > prcgap_rulegraph.svg
```

> Save the rendered SVG/PNG into the docs site (e.g. `docs/images/`) when publishing the documentation, and embed it here.

## Inter-module dependencies

PRCGAP is organized so that BAM refinement is the foundation, and downstream variant / methylation / copy-number modules consume the refined BAMs.

```
                          ┌────────────────────┐
                          │     bam_refiner    │
                          │  (per sample &     │
                          │   per seqtype)     │
                          └─────────┬──────────┘
                                    │
        ┌───────────────┬───────────┼────────────┬──────────────┐
        ▼               ▼           ▼            ▼              ▼
   methylation     copynumber    nanomonsv     clairs       deepsomatic
                                    │            │              │
                                    ▼            ▼              ▼
                              postprocess   point_mutation  point_mutation
                              insert classify  postprocess    postprocess
                              connect
                              HiFi/ONT merge
```

### NanoMonSV pipeline

NanoMonSV runs as an internal pipeline per seqtype (HiFi and ONT), then merges the two callsets:

```
parse → get → postprocess → insert classify → connect → HiFi/ONT merge
```

- `parse` and `get` (tumor + normal) extract candidate SVs from refined BAMs.
- `postprocess` filters and annotates.
- `insert classify` types insertion events.
- `connect` joins fragmented SV calls.
- The HiFi and ONT callsets are merged into a unified per-tumor SV table.

### Point mutation post-processing

Both ClairS and DeepSomatic produce raw VCFs that go through `point_mutation_postprocess`, which performs realignment, pileup, and haplotype-aware refinement.

## Rule file map

PRCGAP's Snakemake rules live under `PRCGAP/workflow/rules/`. The workflow is composed by importing modular rule files:

| File | Role |
|------|------|
| `commons.smk` | Shared utilities, sample sheet loading, helper functions |
| `process.smk` | Top-level imports tying the rule files together |
| `bam_refiner.smk` | Read alignment to phased de novo assemblies (per sample, per seqtype) |
| `methylation.smk` | Methylation calling (HiFi: pb-CpG-tools; ONT: modkit) |
| `copynumber.smk` | Copy number profiling |
| `nanomonsv.smk` | NanoMonSV parse / get / insert classify / postprocess / connect / merge |
| `clairs.smk` | ClairS somatic variant calling and post-processing |
| `deepsomatic.smk` | DeepSomatic somatic variant calling and post-processing |

Tool-specific wrapper scripts live alongside in `PRCGAP/workflow/scripts/`, and JSON Schemas for validating `config.yaml` and `samplesheet.tsv` live in `PRCGAP/workflow/schemas/`.

## Output directory layout

All paths are relative to the run directory (`--directory`):

```
output/
├── bam_refiner/{sample}/{seqtype}/         # Refined BAMs per sample × seqtype
├── methylation/{sample}/{seqtype}/         # Methylation calls per sample × seqtype
├── copynumber/{tumor}/                     # Copy number results per tumor
├── nanomonsv/{seqtype}/                    # Per-seqtype SV outputs (HiFi or ONT)
├── nanomonsv/{tumor}.*.merged.txt          # Merged HiFi/ONT SV calls per tumor
├── clairs/{tumor}/                         # ClairS raw calls
├── clairs_post/{tumor}/                    # ClairS post-processed calls
├── deepsomatic/{tumor}/                    # DeepSomatic raw calls
├── deepsomatic_post/{tumor}/               # DeepSomatic post-processed calls
└── logs/                                   # Per-rule log files
```

`{seqtype}` is `hifi` or `ont`; `{tumor}` is the sample name of the tumor sample for that pair.

## Where to look when something goes wrong

- Snakemake driver logs: `.snakemake/log/`
- Per-rule logs: `output/logs/<module>/<sample>/...`
- Cluster job stderr/stdout: depends on profile (`PRCGAP/profile/uge/` writes via `qsub_submit.sh`; `PRCGAP/profile/slurm/` via `slurm_submit.sh`).
- Validation errors from `config.yaml` / `samplesheet.tsv`: refer to the schemas in `PRCGAP/workflow/schemas/`.

For the practical command sequence and a worked example, see [Example.md](./Example.md).
