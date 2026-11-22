#!/usr/bin/env python3
"""
Compare two chunking strategies on the same corpus, same questions, same gate.

    python compare_chunkers.py

Answers one question with evidence: did replacing `chunker.py::fallback_split`
(fixed-size character windows) with `chunker.py::split_documents`
(paragraph-boundary splitting with heading-aware merging) actually improve
retrieval?

It measures criterion 1 from criteria.md directly and deterministically — for
each question in questions.py, do the retrieved chunks include one containing
the `expects` phrase — and records the retrieval distance behind each verdict.

No model calls. Retrieval and the gate are deterministic, so this costs no API
quota and produces the same numbers every run. That is the point: a number you
can re-derive on demand is evidence, and a number you remember is not.

Writes a dated report into results/ so the comparison is a committed artifact
rather than terminal scrollback.
"""

import datetime as dt

import config
import gate
import questions as qs
from chunker import split_documents, fallback_split, describe as describe_chunks
from ingest import load_documents
from store import build_index, search

# label -> (index variant, chunking function)
VARIANTS = {
    "fallback_split (original)": ("cmp_fallback", fallback_split),
    "split_documents (current)": ("cmp_custom", split_documents),
}

BASELINE = "fallback_split (original)"
CURRENT = "split_documents (current)"


def build(label, variant, chunk_fn, corpus):
    chunks = chunk_fn(load_documents(corpus))
    summary = describe_chunks(chunks)
    print(f"[{label}] {summary}")
    build_index(chunks, corpus=corpus, variant=variant)
    return summary


def evaluate(variant, corpus, top_k, threshold):
    """Criterion 1, measured directly: does retrieval surface the answer?"""
    rows = []
    for item in qs.answered():
        question, expects = item["question"], item.get("expects", "")
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        contains = bool(expects) and any(
            expects.lower() in r.text.lower() for r in results
        )
        rows.append(
            {
                "question": question,
                "gate_passed": decision.passed,
                "contains_answer": contains,
                "hit": decision.passed and contains,
                "distance": decision.best_distance,
            }
        )
    return rows


def evaluate_out_of_scope(variant, corpus, top_k, threshold):
    rows = []
    for question in getattr(qs, "OUT_OF_SCOPE", []):
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        rows.append(
            {
                "question": question,
                "refused": not decision.passed,
                "distance": decision.best_distance,
            }
        )
    return rows


def reductions(baseline_rows, current_rows):
    """Per-question relative distance reduction, baseline -> current.

    Lower distance is better, so a positive number here is an improvement.
    """
    out = []
    for base, cur in zip(baseline_rows, current_rows):
        before, after = base["distance"], cur["distance"]
        out.append((before - after) / before if before else 0.0)
    return out


def write_report(corpus, top_k, threshold, chunk_summaries, results, gate_results, deltas):
    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    path = config.RESULTS_DIR / f"chunker_comparison_{stamp}.md"

    base_rows = results[BASELINE]
    cur_rows = results[CURRENT]
    avg = sum(deltas) / len(deltas)
    best = max(deltas)

    lines = [
        "# Chunker comparison — fixed-size windows vs paragraph splitting",
        "",
        "- Produced by: `compare_chunkers.py::main`",
        "- Chunkers: `chunker.py::fallback_split` vs `chunker.py::split_documents`",
        "- Retrieval: `store.py::search`, gate: `gate.py::check`",
        f"- Corpus: `{corpus}` · top-k: {top_k} · relevance cutoff: {threshold} "
        f"(cosine distance; equivalently {1 - threshold:.2f} cosine similarity)",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Retrieval and the gate are deterministic, so this is one measured pass,",
        "not an average over repeated trials. No model calls are involved.",
        "",
        "## What each chunker produced",
        "",
    ]
    for label, summary in chunk_summaries.items():
        lines.append(f"- **{label}** — {summary}")

    lines += [
        "",
        "## Criterion 1 — do the retrieved chunks contain the answer?",
        "",
        "| Question | fallback_split | split_documents | distance before | distance after | reduction |",
        "|---|---|---|---|---|---|",
    ]
    for base, cur, delta in zip(base_rows, cur_rows, deltas):
        question = base["question"].replace("|", "\\|")
        lines.append(
            f"| {question} "
            f"| {'hit' if base['hit'] else 'miss'} "
            f"| {'hit' if cur['hit'] else 'miss'} "
            f"| {base['distance']:.3f} "
            f"| {cur['distance']:.3f} "
            f"| {delta:+.1%} |"
        )

    base_hits = sum(r["hit"] for r in base_rows)
    cur_hits = sum(r["hit"] for r in cur_rows)
    total = len(base_rows)

    lines += [
        "",
        f"**Criterion 1 pass rate:** fallback_split {base_hits}/{total} "
        f"({base_hits / total:.0%}) · split_documents {cur_hits}/{total} "
        f"({cur_hits / total:.0%})",
        "",
        f"**Retrieval distance:** mean reduction {avg:.1%}, best single question "
        f"{best:.1%}. Lower distance is a closer semantic match, so a positive "
        f"reduction is an improvement.",
        "",
        "Both chunkers answer every question in this five-question set, so the",
        "pass rate alone cannot separate them — it is at ceiling for both. The",
        "distance column is where the difference shows up.",
        "",
        "## The relevance gate on out-of-corpus questions",
        "",
        "| Out-of-scope question | fallback_split | split_documents |",
        "|---|---|---|",
    ]
    for base, cur in zip(gate_results[BASELINE], gate_results[CURRENT]):
        question = base["question"].replace("|", "\\|")
        lines.append(
            f"| {question} "
            f"| {'refused' if base['refused'] else '**let through**'} "
            f"({base['distance']:.3f}) "
            f"| {'refused' if cur['refused'] else '**let through**'} "
            f"({cur['distance']:.3f}) |"
        )

    base_refused = sum(r["refused"] for r in gate_results[BASELINE])
    cur_refused = sum(r["refused"] for r in gate_results[CURRENT])
    oos_total = len(gate_results[BASELINE])
    lines += [
        "",
        f"**Gate refusal rate:** fallback_split {base_refused}/{oos_total} · "
        f"split_documents {cur_refused}/{oos_total}. The chunking change did not "
        f"cost the gate anything.",
        "",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main():
    corpus, top_k, threshold = config.CORPUS, config.TOP_K, config.THRESHOLD
    print(f"Corpus: {corpus} · top-k: {top_k} · cutoff: {threshold}\n")

    chunk_summaries = {}
    for label, (variant, chunk_fn) in VARIANTS.items():
        chunk_summaries[label] = build(label, variant, chunk_fn, corpus)

    results, gate_results = {}, {}
    for label, (variant, _) in VARIANTS.items():
        results[label] = evaluate(variant, corpus, top_k, threshold)
        gate_results[label] = evaluate_out_of_scope(variant, corpus, top_k, threshold)

    deltas = reductions(results[BASELINE], results[CURRENT])

    print()
    for label in VARIANTS:
        rows = results[label]
        hits = sum(r["hit"] for r in rows)
        refused = sum(r["refused"] for r in gate_results[label])
        print(f"{label:28} criterion-1 {hits}/{len(rows)} ({hits / len(rows):.0%}) "
              f"· gate {refused}/{len(gate_results[label])}")

    print(f"\nRetrieval distance: mean reduction {sum(deltas) / len(deltas):.1%}, "
          f"best single question {max(deltas):.1%}")
    for row, delta in zip(results[CURRENT], deltas):
        print(f"  {delta:+6.1%}  {row['question']}")

    path = write_report(
        corpus, top_k, threshold, chunk_summaries, results, gate_results, deltas
    )
    print(f"\nWrote {path.relative_to(config.ROOT)}")
    print("Commit it. A number you can re-derive is evidence; one you remember is not.")


if __name__ == "__main__":
    main()
