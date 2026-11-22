# Campus Q&A RAG Pipeline

By Carlos Huang · Built in CodePath AI 201

A retrieval-augmented question-answering system over 88 campus-life documents: housing, dining, courses, campus jobs and admin deadlines. Ask it something like "is the housing lottery actually random?" and it finds the right documents, answers from them, and names its sources. If the documents don't cover a question, a relevance gate refuses it instead of letting the model guess.

**Stack:** Python · ChromaDB · all-MiniLM-L6-v2 embeddings (384-dim, cosine distance) · Gemini for answers

## Results

- **Better chunking:** I replaced the starter's fixed 800-character windows with paragraph chunks that carry the document's heading. Average retrieval distance dropped **25.8%**, and **53.5%** on the best question. ([full comparison](results/chunker_comparison_2026-11-14_1321.md))
- **Relevance gate:** a 0.6 cosine-distance cutoff (0.40 similarity) refused **5 of 5** out-of-scope questions, like "What is the capital of Mongolia?", and let all 5 in-scope questions through.
- **Answers cite sources:** every answer across 15 runs named at least one source file.
- **Limit:** the test set is 5 in-scope and 5 out-of-scope questions. Both chunkers passed 5 of 5, so I report retrieval distance instead of pass rate to show the difference.

Rerun the chunker comparison: `python compare_chunkers.py`. Setup and other commands are in [`RUNNING.md`](RUNNING.md).

---

# Project write-up

## What This Does

I picked the `campus_life` corpus: 88 short posts written by students about housing, dining halls, course workload, campus jobs and admin deadlines. The system answers practical questions a new student would ask, like how long the lunch line is at Pellew Dining Hall or how many hours a week CS 210 takes. It answers only from the documents and names the file each answer came from.

## Chunking Strategy

**Chunk size:** one paragraph per chunk (167 characters on average, 63 to 397)
**Overlap:** none. Instead, every chunk carries its document's heading.

The starter chunker cut every document into fixed 800-character windows with 120 characters of overlap, and paid no attention to where sentences or paragraphs end. Most `campus_life` posts are shorter than 800 characters, so it just turned each post into one chunk (88 posts, 88 chunks). That meant one chunk could mix several topics, like the good and the bad of a dorm in the same piece.

I changed `split_documents` so it splits on blank lines into paragraphs. That way every chunk is made of complete sentences and covers one idea. A paragraph with no ending punctuation is a heading, not content, so it gets merged into the next paragraph instead of becoming its own chunk. The document's opening heading gets added to every chunk, so even a chunk like "The good: cheapest housing tier by about $900 a year" still says it's about Morrow House.

## Sample Chunks

Produced by `chunker.py::split_documents`:

**Chunk 1** — source: `admin_add_drop_deadline.txt#0`

```
On the add/drop deadline

You can add a course through the end of the second week. Dropping is a longer window — through the end of week six — but a drop after week two shows as a W on your transcript. Nothing anywhere on the registrar's site says this plainly, and students find out from each other.
```

**Chunk 2** — source: `course_cs_340_exams.txt#1`

```
CS 340 Databases — assessment

Start the term project in week three, not week eight; everyone learns this the hard way.
```

**Chunk 3** — source: `course_phys_130_workload.txt#0`

```
Workload for PHYS 130 Mechanics

People keep asking so: 7 hours a week, plus 3 on lab weeks. That's real time, not optimistic time.
```

**Chunk 4** — source: `dining_verrill_street_grill_followup.txt#1`

```
Re: Verrill Street Grill

Also worth saying: one register, so the queue is a single line no matter how busy. Nobody tells you this at orientation.
```

**Chunk 5** — source: `housing_morrow_house.txt#1`

```
Morrow House — what it's actually like

The good: cheapest housing tier by about $900 a year, and the singles are real singles.
```

## Sample Answer

**Question:** is the housing lottery actually random?

**Answer:**

```
The housing lottery is not entirely random for everyone; while rising sophomores get a number drawn at random, juniors and seniors are ordered by accumulated credit hours first, with a random tie-break used only afterwards.
Source: admin_housing_lottery.txt
```

Best distance: 0.248 (passed the gate) · from [`results/run_2026-09-28_2319_after.md`](results/run_2026-09-28_2319_after.md)

## My Relevance Cutoff

**Cutoff:** 0.6 cosine distance (0.40 cosine similarity), set as `THRESHOLD` in `config.py`.

I ran the 5 questions my corpus covers and 5 it clearly doesn't, and wrote down the best distance for each. The two groups didn't overlap: the worst in-corpus question was 0.263 and the best out-of-corpus one was 0.787. I put the cutoff at 0.6, inside that gap, so there's room on both sides.

| Question | In corpus? | Best distance | Gate |
|---|---|---|---|
| is the housing lottery actually random? | Yes | 0.248 | passed |
| how long is the wait at Pellew Dining Hall during peak lunch time? | Yes | 0.132 | passed |
| how many hours a week does a campus job allow during term? | Yes | 0.163 | passed |
| how many hours a week should I expect for CS 210? | Yes | 0.263 | passed |
| when is the best time to do laundry in Tamsin Court? | Yes | 0.124 | passed |
| What is the capital of Mongolia? | No | 0.787 | refused |
| How do I change the oil in a diesel engine? | No | 0.923 | refused |
| Who won the 1994 World Cup? | No | 0.847 | refused |
| What is the recommended dosage of ibuprofen for a headache? | No | 0.849 | refused |
| How do I write a for loop in Rust? | No | 0.860 | refused |

## How I Used AI

**1.** I asked Claude to help me write the chunker functions because I had a pretty good idea of how I wanted it, but I was not sure how to code it, so I directed it to the answer. The starter chunker cut text at a fixed character count, so I changed it to split on paragraphs and output complete sentences, with the heading kept on every chunk.

**2.** I used Claude to learn and digest the material because some of the concepts were not fresh in my brain, like chunking. Once I understood the limitation of the starter chunker, it was easy to change it into a better design.

---

# Unit 2

## Acceptance Criteria

Written before any results existed (full reasoning in [`criteria.md`](criteria.md)):

1. For at least 4 of my 5 test questions, the retrieved chunks include one that contains the answer.
2. Every answer names at least one source document.
3. The relevance gate refuses at least 4 of 5 out-of-corpus questions.
4. At least 4 of 5 sampled chunks cover one topic. *(Revised later; see The Improvement.)*
5. For at least 4 of my 5 in-corpus questions, the gate lets the question through so an answer is attempted.

## Run Log — Before

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks cover one topic | 4 of 5 | 5/5 | not repeated | not repeated | MET |
| 5. Gate lets in-corpus questions through | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |

Criteria 3 and 5 are deterministic (retrieval and a fixed cutoff), so one pass is the whole measurement. Criterion 4 is a manual check of 5 sampled chunks.

Example of real output, produced by `run_eval.py::main` (all 15 answers are in [`results/run_2026-09-27_2145_before.md`](results/run_2026-09-27_2145_before.md)):

**how many hours a week does a campus job allow during term? — run 1**

- Best distance: 0.2427 (passed the gate)
- Sources retrieved: course_cs_210.txt, course_econ_101.txt, course_stat_150.txt, housing_aldridge_hall.txt, money_jobs.txt

```
A campus job allows a maximum of 20 hours a week during term, though most people find 10 to 12 hours is the point where it stops affecting coursework.

Source: money_jobs.txt
```

## Verdicts

| # | Criterion | Target | Verdict | How I decided |
|---|---|---|---|---|
| 1 | Retrieved chunk contains the answer | 4 of 5 | MET | All three runs came back 5 of 5, and I confirmed by hand that each retrieved chunk actually contained the fact, not just a close match. |
| 2 | Every answer names a source | 5 of 5 | MET | I read all 15 generated answers across the three runs, and every one named at least one source file. |
| 3 | Gate stops out-of-corpus questions | 4 of 5 | MET | The gate refused 5 of 5, a single deterministic measurement rather than three separate trials. |
| 4 | Sampled chunks cover one topic | 4 of 5 | MET | All five sampled chunks covered a single topic by the wording of this criterion, though two of them depended on context from an adjacent chunk, which this criterion doesn't ask about. |
| 5 | Gate lets in-corpus questions through | 4 of 5 | MET | All five in-corpus questions passed the gate on every run, again a fixed check rather than a re-rolled one. |

## Diagnoses

No original criterion was missed. But passing these tests doesn't tell me much beyond these small tests, so I looked closer at the chunks themselves.

Two of my sampled chunks started mid-thought. One began with "Also worth saying:" and another with "The good:", and both referred to content that landed in a different chunk. The split separated those passages from the context needed to understand them. If one got retrieved alone, the model would see half a comparison with no idea what the other half was. My runs didn't show this causing a wrong answer, but my criterion 4 ("covers one topic") let both chunks pass, so it couldn't catch the problem.

## The Improvement

**What I changed:** I revised criterion 4 and changed the chunking logic to keep the context needed to understand a passage. Now the document's heading travels with every chunk, so a chunk always names what it's about.

**Revised criterion 4:** At least 4 of 5 sampled chunks must explicitly name the specific thing their content describes, for example "Tamsin Court" rather than just "the hall." The name must appear in the chunk's text or an included heading; a filename or an adjacent chunk doesn't count.

**Why I picked it:** I had direct evidence that criterion 4 was broken as written. Chunks starting with "Also worth saying:" and "The good:" passed "covers one topic" even though they made no sense on their own. That's a real retrieval problem, not a guess, so it was the right thing to fix.

### Run Log — After

Produced by `run_eval.py::main` on 2026-09-28 with the new `split_documents` ([`results/run_2026-09-28_2319_after.md`](results/run_2026-09-28_2319_after.md)).

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Sampled chunks name their subject (revised) | 4 of 5 | 5/5 | not repeated | not repeated | MET |
| 5. Gate lets in-corpus questions through | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |

Revised criterion 4 was re-checked on 2026-11-22 against the five sample chunks above. All five now name their subject through the heading: the add/drop deadline, CS 340, PHYS 130, Verrill Street Grill and Morrow House.

**Did it help?**

Yes. The pass rates were already 5 of 5 before the change, so they couldn't show any difference. Retrieval distance does. On the same 5 questions, with the same top-5 retrieval and cutoff:

| | Before (fixed 800-char windows) | After (paragraph chunks + heading) |
|---|---|---|
| Chunks | 88, 317 characters on average | 183, 167 characters on average |
| Questions answered | 5 of 5 | 5 of 5 |
| Out-of-scope refused | 5 of 5 | 5 of 5 |
| Retrieval distance | baseline | **25.8% lower on average**, 53.5% on the best question |

Lower distance means the retrieved chunk is a closer match to the question. The change didn't cost the gate anything. Full numbers: [`results/chunker_comparison_2026-11-14_1321.md`](results/chunker_comparison_2026-11-14_1321.md).

## What's Still Broken

Based on my tests, nothing is broken: every question passes. That mostly says my test set is too easy. Next I'd design questions that can fail, like questions whose answer is split across two chunks, questions that need a number from one document and a condition from another, and out-of-scope questions that sound close to campus life (for example, a dorm at a different school).

## What I'd Do Differently

I would rewrite criterion 1, "For at least 4 of my 5 test questions, the retrieved chunks include one that contains the answer," because needing just one retrieved chunk that contains the answer seems too lenient to be a real criterion. A stricter version would require the answer to be in the top-ranked chunk.