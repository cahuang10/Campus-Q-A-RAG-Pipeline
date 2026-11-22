# Chunker comparison — fixed-size windows vs paragraph splitting

- Produced by: `compare_chunkers.py::main`
- Chunkers: `chunker.py::fallback_split` vs `chunker.py::split_documents`
- Retrieval: `store.py::search`, gate: `gate.py::check`
- Corpus: `campus_life` · top-k: 5 · relevance cutoff: 0.6 (cosine distance; equivalently 0.40 cosine similarity)
- When: 2026-11-14 13:21

Retrieval and the gate are deterministic, so this is one measured pass,
not an average over repeated trials. No model calls are involved.

## What each chunker produced

- **fallback_split (original)** — 88 chunks, 317 characters on average (shortest 178, longest 549), produced by chunker.py::fallback_split
- **split_documents (current)** — 183 chunks, 167 characters on average (shortest 63, longest 397), produced by chunker.py::split_documents

## Criterion 1 — do the retrieved chunks contain the answer?

| Question | fallback_split | split_documents | distance before | distance after | reduction |
|---|---|---|---|---|---|
| is the housing lottery actually random? | hit | hit | 0.248 | 0.248 | +0.0% |
| how long is the wait at Pellew Dining Hall during peak lunch time? | hit | hit | 0.157 | 0.132 | +15.9% |
| how many hours a week does a campus job allow during term? | hit | hit | 0.350 | 0.163 | +53.5% |
| how many hours a week should I expect for CS 210? | hit | hit | 0.297 | 0.263 | +11.4% |
| when is the best time to do laundry in Tamsin Court? | hit | hit | 0.239 | 0.124 | +48.1% |

**Criterion 1 pass rate:** fallback_split 5/5 (100%) · split_documents 5/5 (100%)

**Retrieval distance:** mean reduction 25.8%, best single question 53.5%. Lower distance is a closer semantic match, so a positive reduction is an improvement.

Both chunkers answer every question in this five-question set, so the
pass rate alone cannot separate them — it is at ceiling for both. The
distance column is where the difference shows up.

## The relevance gate on out-of-corpus questions

| Out-of-scope question | fallback_split | split_documents |
|---|---|---|
| What is the capital of Mongolia? | refused (0.825) | refused (0.787) |
| How do I change the oil in a diesel engine? | refused (0.934) | refused (0.923) |
| Who won the 1994 World Cup? | refused (0.886) | refused (0.847) |
| What is the recommended dosage of ibuprofen for a headache? | refused (0.844) | refused (0.849) |
| How do I write a for loop in Rust? | refused (0.896) | refused (0.860) |

**Gate refusal rate:** fallback_split 5/5 · split_documents 5/5. The chunking change did not cost the gate anything.
