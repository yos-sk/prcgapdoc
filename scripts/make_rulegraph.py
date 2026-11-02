#!/usr/bin/env python3
"""
Turn the output of `snakemake --rulegraph` into the clustered rule graph shown on
the Workflow page (docs/plot/prcgap_rulegraph.svg).

Rules are grouped by the step numbers of the Workflow page (§0-§9), and each
cluster is labelled with the output directory of that step. From v0.2, the
per-chunk `deepsomatic` rule runs after the `deepsomatic_chunks` checkpoint, so it
is not in the rule graph that snakemake prints before the run; it is added back
here (dashed).

Usage:
    snakemake --snakefile PRCGAP/workflow/Snakefile --configfile config.yaml \
        --directory OUTPUT --rulegraph > rulegraph.dot
    python3 make_rulegraph.py rulegraph.dot prcgap_rulegraph.dot
    dot -Tsvg prcgap_rulegraph.dot > ../docs/plot/prcgap_rulegraph.svg
"""
import re
import sys

# (cluster id, label, fill colour, border colour, rule-name predicate)
STEPS = [
    ("s0", "§0 Assembly annotation\nannotation/", "#E3F2FD", "#1565C0",
     lambda r: r.startswith(("dna_brnn", "liftoff", "prepare_mask_regions", "chain_files",
                             "line1", "simple_repeat"))),
    ("s1", "§1 BAM Refiner\nbam_refiner/", "#E8F5E9", "#2E7D32",
     lambda r: r.startswith("bam_refiner")),
    ("s2", "§2 Methylation\nmethylation/", "#FFF3E0", "#E65100",
     lambda r: r.startswith("methylation")),
    ("s3", "§3 Copy number\ncopynumber/", "#FFF3E0", "#E65100",
     lambda r: r.startswith("copynumber")),
    ("s4", "§4 Nanomonsv (per seqtype)\nnanomonsv/{seqtype}/", "#FFF3E0", "#E65100",
     lambda r: r.startswith("nanomonsv") or r == "assembly_bwa_index"),
    ("s5", "§5 DeepSomatic\ndeepsomatic/", "#FFF3E0", "#E65100",
     lambda r: r.startswith("deepsomatic") and "postprocess" not in r),
    ("s7", "§7 Point mutation post-processing\ndeepsomatic_post/", "#FFE0B2", "#E65100",
     lambda r: r.startswith("deepsomatic_postprocess")),
    ("s8", "§8 SV annotation\nannotate_sv/", "#F3E5F5", "#6A1B9A",
     lambda r: r in ("gff_to_bed", "prep_sv", "annotate_sv_main", "reclassify_sv")
     or r.startswith("coordconv_sv")),
    ("s9", "§9 SNV / INDEL annotation\nannotate_snv/, annotate_indel/", "#F3E5F5", "#6A1B9A",
     lambda r: r in ("mut_vcf_index", "prep_mut", "bed2vcf_indel", "indel_hap_reference",
                     "annotate_mut_main")
     or r.startswith(("coordconv_snv", "liftvcf_indel"))),
]


def main(src, dst):
    text = open(src).read()
    labels = dict(re.findall(r'\t(\d+)\[label = "([^"]+)"', text))
    edges = re.findall(r'\t(\d+) -> (\d+)', text)

    # Add the per-chunk caller between the checkpoint and the merge.
    by_name = {v: k for k, v in labels.items()}
    added = None
    if "deepsomatic" not in by_name and "deepsomatic_chunks" in by_name:
        new_id = str(max(int(k) for k in labels) + 1)
        labels[new_id] = "deepsomatic"
        added = new_id
        chunks, merge = by_name["deepsomatic_chunks"], by_name["deepsomatic_merge"]
        edges = [e for e in edges if e != (chunks, merge)]
        edges += [(chunks, new_id), (new_id, merge)]
        # bam_refiner output is an input of every chunk
        for k, v in labels.items():
            if v.startswith("bam_refiner_") and (k, by_name["deepsomatic_scatter_setup"]) in edges:
                edges.append((k, new_id))

    out = [
        "digraph prcgap_rulegraph {",
        '  graph [rankdir=TB, bgcolor="transparent", fontname="Helvetica", fontsize=13,',
        '         nodesep=0.25, ranksep=0.35];',
        '  node  [shape=box, style="rounded,filled", fillcolor="white", color="#546E7A",',
        '         fontname="Helvetica", fontsize=10, penwidth=1.2];',
        '  edge  [color="#90A4AE", penwidth=1.0, arrowsize=0.6];',
    ]
    placed = set()
    step_of = {}
    for cid, label, fill, border, pred in STEPS:
        members = [k for k, v in labels.items() if pred(v)]
        if not members:
            continue
        out.append(f"  subgraph cluster_{cid} {{")
        out.append(f'    label="{label}"; labeljust="l"; style="rounded,filled";'
                   f' fillcolor="{fill}"; color="{border}"; fontcolor="{border}";')
        for k in members:
            extra = ', style="rounded,filled,dashed", xlabel="per chunk"' if k == added else ""
            out.append(f'    n{k} [label="{labels[k]}"{extra}];')
            placed.add(k)
            step_of[k] = cid
        out.append("  }")
    # `all` only collects the leaves; drawing it adds long edges and no information.
    drop = {k for k, v in labels.items() if v == "all"}
    for k, v in labels.items():
        if k not in placed and k not in drop:
            out.append(f'  n{k} [label="{v}"];')
    # Colour the long fan-out edges by source so they can be told apart from the
    # within-step chains: annotation inputs (§0) dashed blue, refined BAMs (§1) green.
    edge_style = {
        "s0": ' [color="#64B5F6", style=dashed]',
        "s1": ' [color="#81C784"]',
    }
    for a, b in edges:
        if a in drop or b in drop:
            continue
        style = edge_style.get(step_of.get(a), "") if step_of.get(a) != step_of.get(b) else ""
        out.append(f"  n{a} -> n{b}{style};")
    out.append("}")
    open(dst, "w").write("\n".join(out) + "\n")

    unplaced = [labels[k] for k in labels if k not in placed and labels[k] != "all"]
    if unplaced:
        sys.stderr.write("rules without a step: " + ", ".join(unplaced) + "\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
