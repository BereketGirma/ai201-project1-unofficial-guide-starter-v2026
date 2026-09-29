# The Unofficial Guide

Bereket Girma — corpus: `advice_threads`

---

# Unit 1

## What This Does

This is a retrieval system over `advice_threads`, a corpus of 23
question-and-answer threads about university life — 75 replies in total,
covering things like whether a parking permit is worth the August scramble,
how much RAM a CS student actually needs, and what happens if you hand work in
late. You ask a plain question and it answers from the replies themselves,
naming the thread it drew from. It answers questions whose answer a student
actually wrote down somewhere in those threads; for anything else, it refuses
rather than guessing. The defining feature of this corpus is that the replies
argue with each other, so a good answer here often has to report a
disagreement rather than a fact.

## Chunking Strategy

**Chunk size:** one reply — 105 to 254 characters in practice, 175 on average,
with a hard ceiling of 400 (`config.MAX_CHUNK_CHARS`)
**Overlap:** no sliding window. Every chunk instead repeats its thread's
`THREAD:` question line, 40 to 70 characters of shared context

Every document in this corpus has the same shape: a `THREAD:` question, then
two to five replies marked `--- reply N (X votes) ---`. I checked that against
all 23 documents before writing anything, and it holds for every one of them.
That made the reply, not a character count, the obvious unit — one reply is one
person's complete take on the question.

The starter's fixed 800-character windows ignored that structure and got it
wrong in two different directions at once. Most threads are under 800
characters, so they came through whole: four disagreeing answers embedded as a
single vector, matching every question about that topic a little and none of
them well. The few threads that overran got cut at whatever character 800
landed on — including one 2-character chunk that is the tail of a sentence and
can never match anything. 23 documents became 26 chunks, which tells you how
little splitting was actually happening.

**I changed my mind about one thing partway through.** Splitting per reply has
an obvious cost, and I nearly rejected the idea because of it. Reply 3 of
`thread_bike_commute.txt` reads *"Both true. I keep a cheap bike for September
to November and walk the rest of the year."* On its own that answers nothing —
you cannot tell what is both true, or what the bike is being compared against.
My first instinct was that replies therefore had to stay glued to their
neighbours. What changed my mind was realising the missing context is always
the same 50 characters: the thread's question. Prefixing it to every chunk
keeps the reply legible without dragging in the arguments around it. That
repeated question line is this chunker's version of overlap, and it is more
useful than a sliding window would be, because the shared text is the thing
that makes the chunk mean something rather than an arbitrary tail of whatever
came before.

Result: 26 chunks became 75, the shortest went from 2 characters to 105, and
the longest from 793 to 254.

## Sample Chunks

All five produced by `chunker.py::split_documents`.

**Chunk 1** — source: `thread_bike_commute.txt#0` — produced by: `chunker.py::split_documents`

```
THREAD: Is a bike worth it for a 20 minute walk commute?

Yeah. Cuts an 18 minute walk to about 6. The thing nobody mentions is storage — covered bike parking exists at three buildings and is full by 9am at all three.
```

**Chunk 2** — source: `thread_first_gen.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Anything specific for first-generation students?

The thing I'd say: the unwritten rules are the hard part, not the coursework. Ask about the unwritten rules explicitly. People are happy to explain them and nobody volunteers them.
```

**Chunk 3** — source: `thread_laptop_specs.txt#2` — produced by: `chunker.py::split_documents`

```
THREAD: How much laptop do I actually need for CS courses?

I did two years on an 8GB machine and it was fine until the last project, at which point it very much wasn't. 16 is the answer.
```

**Chunk 4** — source: `thread_parking.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Worth getting a parking permit?

Street parking on Verrill is legal and free and unmarked, which is why half the upper years do it.
```

**Chunk 5** — source: `thread_sleep_schedule.txt#1` — produced by: `chunker.py::split_documents`

```
THREAD: Everyone says fix your sleep. Does it actually matter?

The library being open until 2am is a trap. It's a resource, not a schedule.
```

Chunks 3 and 5 are the ones that show why the prefix matters. *"16 is the
answer"* and *"the library being open until 2am is a trap"* are both useless
in isolation and both perfectly clear with the question above them.

## Sample Answer

**Question:** Do students recommend keeping a bike through the winter here?

**Answer:**

```
  (best distance 0.443, cutoff 0.7)

No, one commenter mentions selling their bike because salt and ice between
November and March destroy the drivetrain in one season, while another notes
they only use a cheap bike from September to November and walk the rest of the
year (thread_bike_commute.txt).

Sources retrieved: thread_bike_commute.txt, thread_winter_advice.txt
```

This is the answer I most wanted to get right, because the four replies in
that thread disagree — reply 1 is enthusiastic, reply 2 sold their bike, reply
3 splits the difference. The answer reports the disagreement instead of
picking the first reply and presenting it as consensus.

And a question the corpus does not cover, refused before the model is called
at all:

```
$ python app.py ask "What is the capital of Mongolia?"
  (best distance 0.899, cutoff 0.7)

I don't have enough information about that.

0 model calls this session
```

**My relevance cutoff:** `0.70`, set in `config.py`.

I ran my five test questions and the five in `OUT_OF_SCOPE` through retrieval
and recorded the best distance for each. The two groups separate cleanly, with
a 0.230-wide gap and nothing sitting in it. 0.70 is near the midpoint of that
gap (0.704), which leaves my worst real question 0.111 of margin and the
nearest out-of-scope question 0.119 on the other side.

I did not keep the shipped 0.6. It would still have passed all five in-corpus
questions, but only by 0.011 on Q4 — that is not margin, it is luck, and any
change to the chunking would have moved a real question to the wrong side of
it.

| Question | In corpus? | Best distance |
|---|---|---|
| How much RAM do students say is worth paying for on a laptop for CS courses? | yes | 0.129 |
| If a syllabus doesn't state an email response window, how long should I wait before following up with a professor? | yes | 0.202 |
| How many black-and-white pages does the printing quota cover? | yes | 0.310 |
| Do students recommend keeping a bike through the winter here? | yes | 0.443 |
| What is the most reliable way to get an extension on a late assignment? | yes | 0.589 |
| What is the recommended dosage of ibuprofen for a headache? | no | 0.819 |
| How do I write a for loop in Rust? | no | 0.861 |
| Who won the 1994 World Cup? | no | 0.898 |
| What is the capital of Mongolia? | no | 0.899 |
| How do I change the oil in a diesel engine? | no | 0.905 |

Q4 — the extension question — is the interesting row. It is a real question
with a real answer in `thread_late_work.txt`, and it sits 0.146 further out
than my next-worst question. I have left it in deliberately rather than
rewording it to something easier, because it is the row that makes the cutoff
a decision rather than a number.

## How I Used AI

**1. Writing the per-reply chunker.** I had worked out from reading the
documents that every thread was a `THREAD:` line plus `--- reply N ---`
markers, and I asked Claude to turn that into a replacement for
`split_documents`. What came back included something I had not asked for: a
`_split_oversized` helper that windows a reply too long to fit under the
400-character ceiling. No reply in this corpus comes close — the longest is
195 characters — so the branch never executes. I kept it anyway, but changed
why it is there and said so in the docstring: criterion 4 claims every chunk
is under 400 characters, and with that helper the claim is guaranteed by the
code instead of being true by accident on this particular corpus.

**2. A prediction that turned out to be wrong, which was the useful part.**
Before re-chunking, Q4 came back at 0.591 and I asked Claude why. It argued
that `thread_late_work.txt` is titled *"What actually happens if you hand
something in late?"* — a different question from "how do I get an extension" —
and that with the whole thread as one chunk, the title was dragging the
embedding toward consequences and away from the answer. The prediction was
that splitting per reply would pull the distance in. I re-chunked and it went
to 0.589: essentially unchanged, and the top hit moved to a completely
different document. So the explanation was wrong. The real problem is that
*"the most reliable way to get an extension"* and *"ask before the deadline,
not after"* share almost no vocabulary, which is a retrieval problem and not a
chunking one. I would not have located that if the prediction had been right,
and it is the first thing I intend to test in unit 2.

<!-- ── Stretch features ─────────────────────────────────────────────────────
     Doing one? Say so here BEFORE you start. A feature this README never
     claims earns nothing.
     ───────────────────────────────────────────────────────────────────────── -->

---

# Unit 2

Same system, same corpus, same repository. The only change to the pipeline in
this unit is the improvement in *The Improvement* below.

**A measurement bug I had to fix before any of this meant anything.** The
`scorer.py` I wrote in class was one line:

```python
return expects.strip().lower() in (answer or "".lower())
```

`.lower()` binds to `""`, not to `answer` — Python reads it as
`answer or ("".lower())` — so the answer never got lowercased and the match was
case-sensitive on one side only. `"16gb" in "...16GB..."` is `False`. That
marked Q2 failed on all three runs of `results/run_2026-09-23_2020_before.md`
even though every one of those answers says "16GB". The system was right and my
scorer was wrong. I fixed it and re-ran the baseline, because a before/after
comparison measured with a broken instrument tells you nothing. `scorer.py` is
test instrumentation rather than part of the pipeline, so fixing it is not the
one change this unit allows me — it is what makes the one change measurable.

**Measuring five criteria needed a second script.** `run_eval.py` produces one
row per question and `judge` returns a single bool, which cannot carry five
criteria that measure five different things. `check_criteria.py` does the
aggregation into the criterion-level tables below. Only criterion 2 depends on
generated text, and it reads that from the committed `run_eval.py` report rather
than regenerating it, so every table here is re-derivable from the evidence
files in `results/` and running it costs no model calls.

## Run Log — Before

Produced by `run_eval.py::main` (`results/run_2026-09-27_1544_before.md`) and
aggregated by `check_criteria.py::main`
(`results/criteria_2026-09-27_1548_before.md`). Semantic retrieval only —
reproducible from the current code with `AI201_HYBRID=0`.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Chunks 80-400 chars and carry a THREAD: line | all 75 | 75/75 | 75/75 | 75/75 | MET |
| 5. No in-corpus question refused | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |

Criteria 1, 3, 4 and 5 are identical across the three run columns, and that is
correct rather than lazy: embedding a question returns the same vector every
time, the gate is a comparison against a fixed number, and the chunker is a pure
function of the documents. Criterion 2 is the only one that can move between
runs, because it is the only one that depends on what the model wrote. It did
not move.

### Real output

**Criterion 1** — `check_criteria.py::criterion_1`, over chunks from
`store.py::search`. The rank column is the position of the chunk that actually
contains the answer:

```
| Question | Expects | Answer lives in | Found at rank | Top-1 chunk | Best distance |
| Q1 printing quota    | `600`                 | thread_printing.txt        | 1 | thread_printing.txt#0          | 0.310 |
| Q2 laptop RAM        | `16GB`                | thread_laptop_specs.txt    | 1 | thread_laptop_specs.txt#0      | 0.129 |
| Q3 email window      | `48 hours`            | thread_professor_email.txt | 1 | thread_professor_email.txt#0   | 0.202 |
| Q4 extension         | `before the deadline` | thread_late_work.txt       | 4 | thread_first_year_regret.txt#1 | 0.589 |
| Q5 winter bike       | `salt`                | thread_bike_commute.txt    | 1 | thread_bike_commute.txt#1      | 0.443 |
```

Q4's full ranking, which is the row that matters:

```
#  chunk                            dist   body
1  thread_first_year_regret.txt#1  0.589   That you can take a course pass/fail and declare it late...
2  thread_group_project.txt#1      0.602   Most instructors here will adjust individual grades if you raise it before the deadline...
3  thread_group_project.txt#0      0.635   Document early. Not to be difficult...
4  thread_late_work.txt#1          0.673   The universal rule: ask before the deadline, not after...   <-- the answer
5  thread_late_work.txt#2          0.685   Documented illness goes through the dean of students...
```

**Criterion 2** — `scorer.py::names_source` over every answer in the report.
All 15 named a source. Q1, run 1, from `generate.py::answer_from_chunks`:

```
The printing quota of $30 covers about 600 black-and-white pages (from thread_printing.txt).
```

**Criterion 3** — `run_eval.py::check_out_of_scope`, cutoff 0.70. Refused 5 of 5:

```
| What is the capital of Mongolia?                          | 0.899 | refused |
| How do I change the oil in a diesel engine?               | 0.905 | refused |
| Who won the 1994 World Cup?                               | 0.898 | refused |
| What is the recommended dosage of ibuprofen for a headache?| 0.819 | refused |
| How do I write a for loop in Rust?                        | 0.861 | refused |
```

**Criterion 4** — `check_criteria.py::criterion_4` over all 75 chunks from
`chunker.py::split_documents`:

```
75 chunks, 175 characters on average (shortest 105, longest 254),
produced by chunker.py::split_documents
75 of 75 are between 80 and 400 characters and contain a `THREAD:` line.
No chunk violates either half of the criterion.
```

**Criterion 5** — `check_criteria.py::criterion_5`, cutoff 0.70. Passed 5 of 5,
worst margin 0.111 on Q4:

```
| Q2 laptop RAM     | 0.129 | passed |
| Q3 email window   | 0.202 | passed |
| Q1 printing quota | 0.310 | passed |
| Q5 winter bike    | 0.443 | passed |
| Q4 extension      | 0.589 | passed |
```

## Verdicts

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 | Retrieved chunk contains the answer (4 of 5) | **MET** | 5 of 5. The answer-bearing chunk was in the returned set for every question. It is MET on the revised wording too, which is the stricter reading — see the note below. |
| 2 | Every answer names a source (5 of 5) | **MET** | 15 of 15 answers across three runs matched `thread_*.txt`. No run came in under 5 of 5, so the target holds rather than showing up occasionally. |
| 3 | Gate stops out-of-corpus questions (4 of 5) | **MET** | 5 of 5 refused. The nearest out-of-scope question was 0.819 against a 0.70 cutoff, so this was not close. |
| 4 | Chunks 80-400 chars and carry a `THREAD:` line (all 75) | **MET** | Scripted over all 75 chunks, zero violations. Shortest 105, longest 254, every chunk carrying its `THREAD:` line. |
| 5 | No in-corpus question refused (5 of 5) | **MET** | All five passed. The worst was Q4 at 0.589 against 0.70 — 0.111 of margin, which is the margin I predicted in unit 1 when I moved the cutoff off 0.6. |

**I revised criterion 1, and it did not change the verdict.** The original
wording — "the retrieved chunks include one that contains the answer" — can be
satisfied by the wrong document. Q4 expects the phrase "before the deadline".
That phrase is in `thread_late_work.txt` reply 2, which is the answer. It is
*also* in `thread_group_project.txt` reply 2 — "most instructors here will
adjust individual grades if you raise it before the deadline rather than after"
— which is about group-project grading and answers nothing about extensions.
The `group_project` chunk ranked 2nd and the `late_work` chunk ranked 4th, so a
bare substring check credited the hit to the wrong document and called it a
pass. It was right by accident.

The revision in `criteria.md` requires the hit to come from the document that
actually holds the answer (`answer_in` in `questions.py`). The target stays at
4 of 5 and the before-run comes out 5 of 5 either way, because
`thread_late_work.txt#1` *is* in the top five — just badly ranked. This is a fix
to the measurement, not to the target, and I am flagging that it changed nothing
about the verdict so nobody has to take my word for which kind of change it was.

## Diagnoses

**I missed nothing, and four of my five targets could not realistically have
been missed.** The assignment says to say so honestly rather than treat five
METs as a good result, so:

- **Criterion 2 was close to unmissable by construction.** `generate.py` appends
  the source line from chunk metadata programmatically, and the gate means the
  model is never called with an empty context. I said as much in `criteria.md`
  in unit 1 — "the only way to land under 5 of 5 is a real defect in how sources
  are carried through". That was accurate, and it means the criterion tests
  plumbing that has no reason to vary.
- **Criterion 4 is guaranteed by the code, not by the corpus.**
  `_split_oversized` enforces the 400-character ceiling, and the 80-character
  floor cannot be reached because the shortest reply is 68 characters and every
  chunk gets a 40-70 character `THREAD:` prefix on top. A criterion a helper
  function makes true by construction cannot fail.
- **Criterion 3 was safe and I knew the number that made it safe.** I measured a
  0.230-wide gap with nothing in it before writing the target. I set 4 of 5
  rather than 5 of 5 to leave room for the re-chunk narrowing the gap. It did
  not narrow: the nearest out-of-scope question is 0.819, which is 0.119 clear
  of the cutoff.
- **Criterion 5 had 0.111 of margin on its worst question**, which is the margin
  I deliberately built when I moved the cutoff from 0.6 to 0.70.
- **Criterion 1 was the only one with real risk**, and I calibrated it to absorb
  exactly the failure that showed up. `criteria.md` says "four of five and not
  five of five because Q4 is the one I expect to lose". Q4 *is* the one that
  went wrong — its answer chunk landed at rank 4 behind two chunks that answer
  nothing — but the criterion measures presence in the returned set rather than
  rank, and `top_k` is 5, so a rank-4 hit counts the same as a rank-1 hit.

**The one real failure my test found, which no criterion registered.** Q4's
retrieval is genuinely bad and my criteria cannot see it:

- The top-ranked chunk, `thread_first_year_regret.txt#1` at 0.589, is about
  declaring a course pass/fail. It has nothing to do with extensions.
- Ranks 2 and 3 are both from `thread_group_project.txt`, a different question.
- The answer sits at rank 4.
- **The gate's own number for Q4 comes from an irrelevant chunk.**
  `gate.check` takes `min(distance)`, which is 0.589 — the pass/fail chunk.
  Criterion 5 records Q4 as passing with 0.111 of margin, and that margin is
  supplied by a chunk that answers nothing.

**Stage and mechanism:** this is **retrieval**, specifically embedding-space
proximity, not chunking or generation. The mechanism is vocabulary. Q4 asks for
"the most reliable way to get an **extension** on a **late assignment**". The
answer reads "the universal rule: ask **before the deadline**, not after". The
word "extension" does not appear anywhere in the corpus. "deadline" appears in
the answer but not the question. The only term the question and its answer share
is "late", and that reaches the chunk through the `THREAD:` prefix rather than
the reply itself. A bi-encoder given almost no lexical overlap and a thread
title pointing at consequences rather than at asking early has very little to
work with.

**The pattern, which is what I would have missed by looking at Q4 alone.** The
same mechanism is latent in Q5. This corpus is built out of replies that argue
with each other, and the reply carrying the real answer is very often the
*counterpoint* — so it restates neither the question's vocabulary nor the
thread's premise. Q5 asks "do students recommend keeping a **bike** through the
**winter**?" and its answer is "Counterpoint, I sold mine. Between November and
March the paths are either icy or salted and **salt** destroys a drivetrain."
No "bike" in the body, no "winter", no "recommend". Q4 and Q5 are one problem,
not two: **on this corpus, the more directly a reply answers the question, the
less of the question's vocabulary it tends to contain.** That prediction is what
made Q5 the thing to watch when I changed retrieval, and it is the reason the
improvement below did what it did.

**Which criterion I would tighten, and to what.** Criterion 1, from "the
retrieved chunks include one that contains the answer" to **"for at least 4 of
5 questions, the *top-ranked* chunk comes from the document that holds the
answer."** Before the improvement that would have come out 4 of 5 and still
been MET; after it, 3 of 5 and MISSED. A rank-sensitive criterion would have
caught the regression below. Mine could not.

## The Improvement

**What I changed:** hybrid retrieval. `store.py::search` now ranks every chunk
twice — by cosine distance and by BM25 keyword score (`rank-bm25`, already in
`requirements.txt`) — and fuses the two rankings with reciprocal rank fusion,
`score = sum(1 / (60 + rank))`, in `store.py::_rrf`. New settings are
`config.HYBRID_SEARCH` and `config.RRF_K`.

Two details that decide whether the comparison means anything:

- **The gate is untouched.** Every returned `Result` still carries its true
  cosine distance in both modes. Hybrid changes which chunks come back and in
  what order, never what a distance *says*, so `gate.check` keeps comparing like
  with like and criteria 3 and 5 stay measurable.
- **It is toggleable.** `AI201_HYBRID=0` reproduces the before-run from the
  current code, so the before/after comparison is not against a version of the
  repo that no longer exists.

I fused ranks rather than scores because a cosine distance and a BM25 score are
on unrelated scales with no shared zero; adding them directly would let whichever
has the larger numeric range quietly dominate.

**Why I picked it:** my diagnosis says Q4 fails in retrieval because the question
and its answer share almost no vocabulary and the chunks that outrank the answer
are semantically adjacent but wrong, and hybrid search is the one option on the
Milestone 4 menu that adds a second, independent signal for ranking the same
chunks. My unit 1 README already committed to this: *"that is a retrieval
problem and not a chunking one, and it is the first thing I intend to test in
unit 2."*

**What I expected to go wrong, written before I ran it.** BM25 needs shared
terms, and "extension" appears nowhere in the corpus — the only overlap is
"late". So I expected a small gain at best on Q4, and I expected Q5 to be at
risk for the same reason Q4 was: its answer is a counterpoint reply that omits
the question's vocabulary, while `thread_winter_advice.txt` is stuffed with the
word "winter" and answers nothing about bikes.

### Run Log — After

Produced by `run_eval.py::main` (`results/run_2026-09-27_1550_after.md`) and
aggregated by `check_criteria.py::main`
(`results/criteria_2026-09-27_1550_after.md`).

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Chunks 80-400 chars and carry a THREAD: line | all 75 | 75/75 | 75/75 | 75/75 | MET |
| 5. No in-corpus question refused | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |

**Did it help? On the thing I aimed it at, yes. On my criteria, it changed
nothing. And it broke something my criteria cannot see.**

The verdict table is identical before and after. Every number that moved is
inside a criterion that only asks whether the answer came back at all:

| | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| Rank of the answer chunk, before | 1 | 1 | 1 | **4** | 1 |
| Rank of the answer chunk, after | 1 | 1 | 1 | **2** | **5** |

- **Q4 improved, 4 to 2** — what I aimed at. But not by the mechanism I
  expected. `thread_late_work.txt#1` is semantic rank 4 and only *keyword* rank
  8, so BM25 did not promote it. What moved it up was BM25 *demoting the
  distractor*: `thread_first_year_regret.txt#1` is semantic rank 1 but keyword
  rank 14, and fusion punishes that inconsistency. Hybrid search helped here by
  contributing evidence *against* a wrong chunk, not evidence for the right one.
- **Q5 regressed, 1 to 5** — the risk I wrote down, realised. Its answer chunk
  is semantic rank 1 but keyword rank 11, and `thread_winter_advice.txt#0` —
  "Layers, not a big coat" — is keyword rank 1 because the query says "winter".
  Fusion promoted a chunk containing the question's vocabulary over the chunk
  containing its answer. Q5's answer is now one position from falling out of
  `top_k` entirely.
- **The generated answers survived anyway**, which is why criterion 2 and the
  end-to-end scorer did not move. With `top_k = 5` the answer chunk is still in
  context at rank 5, and the model still found it. Q5, run 2, after:

  ```
  No, students do not recommend keeping a bike through the winter. One student
  writes that they walk instead from November through March because salt
  destroys the drivetrain, while another keeps a cheap bike only from September
  to November.

  Source: `thread_bike_commute.txt`
  ```

- **The gate held.** In-corpus best distances are byte-identical before and
  after, because `min(distance)` over the returned set did not change. Two
  out-of-scope questions shifted — "Who won the 1994 World Cup?" 0.898 → 0.931
  and the Rust question 0.861 → 0.864 — because the returned set changed. Both
  still refused, and both moved further from the cutoff.

**I tried to tune my way out of the trade-off and could not.** `RRF_K` controls
how sharply rank differences count, so I swept it over the whole range rather
than assuming 60 was right:

```
  RRF_K | Q1 | Q2 | Q3 | Q4 | Q5
      1 |  1 |  1 |  1 |  5 |  2
      2 |  1 |  1 |  1 |  5 |  2
      5 |  1 |  1 |  1 |  3 |  4
     10 |  1 |  1 |  1 |  3 |  5
     20 |  1 |  1 |  1 |  2 |  5
     60 |  1 |  1 |  1 |  2 |  5
    200 |  1 |  1 |  1 |  2 |  5
   1000 |  1 |  1 |  1 |  2 |  5
```

No value gets Q4 into the top 2 and keeps Q5 at 1. The reason is structural, not
a matter of finding a better number: a low `RRF_K` makes rank 1 dominant, which
is what Q5 needs, because its answer *is* semantic rank 1. A high `RRF_K`
rewards consistency across both rankings, which is what Q4 needs, because its
distractor is semantic rank 1 and must be demoted. **Q4 needs the fusion to
distrust the semantic top-1 and Q5 needs it to trust it.** One global constant
cannot do both. I shipped 60 because it is the published default and because Q4
is the failure my diagnosis actually named.

## What's Still Broken

Every criterion is MET, so nothing on my list is outstanding. That is the
problem worth reporting: the list is not sensitive enough to register what this
unit found.

1. **Q5's answer chunk is at rank 5 of 5, one position from disappearing.** This
   is a regression I introduced and chose to ship. What I would do: make the
   fusion asymmetric instead of a single constant — keep a chunk that is
   semantic rank 1 from being demoted below some floor, so BM25 can reorder the
   tail without overturning a confident semantic win. I stopped because that is
   a second change to retrieval and this unit allows one, and because inventing
   a fusion rule to fit two data points is how you overfit to five questions.
2. **Q4's gate margin is still supplied by an irrelevant chunk.** `min(distance)`
   for Q4 is 0.589 from `thread_first_year_regret.txt#1`, unchanged, because
   hybrid reordered the set without changing any distance. Criterion 5 reports
   0.111 of margin that the answer chunk did not earn — its real distance is
   0.673, which is only 0.027 clear of the cutoff. I would change the gate to
   test the distance of the *top-ranked* chunk rather than the minimum over the
   set. I did not, because it would change refusal behaviour and I could not
   have attributed the result to hybrid search afterwards.
3. **The lexical mismatch itself is untouched.** "Extension" is not in the
   corpus and no retrieval change makes it appear. The real fix is query-side —
   expansion or a rewrite step that turns "get an extension" into "ask before
   the deadline" — or a cross-encoder reranker that reads the question and the
   chunk together instead of comparing two independently-built vectors. Both are
   larger than this unit's one change.
4. **Five questions is too few to tell a fix from noise.** Q4 gained and Q5 lost
   on a sample of five, and I cannot tell from that whether hybrid retrieval is
   better or worse on this corpus in general. I would want fifteen to twenty
   questions before trusting either direction.

## What I'd Do Differently

**Criterion 1 is the one I would rewrite, and the problem is not the target — it
is that it measures presence instead of position.** "The retrieved chunks
include one that contains the answer" is true whether the answer is rank 1 or
rank 5, so with `top_k = 5` it is nearly a test of whether the document exists.
It stayed MET through a change that halved Q4's rank and quintupled Q5's, which
is the clearest evidence I have that it was measuring the wrong thing. I would
write: *"for at least 4 of 5 questions, the top-ranked chunk comes from the
document that holds the answer."* That is the same kind of claim, one word
stricter, and it would have come out 4 of 5 before and 3 of 5 after — turning an
invisible regression into a MISSED I would have had to explain.

**Criterion 4 I would drop or replace.** `_split_oversized` makes the ceiling
true by construction and the `THREAD:` prefix makes the floor unreachable, so
the criterion cannot fail for any input this corpus can produce. It tests my
chunker's contract with itself. I would replace it with something about whether
a chunk is *independently answerable* — harder to measure, which is precisely
why I avoided it in unit 1, and I now think I avoided it for the wrong reason.

**I would add a criterion about the top-1 chunk being relevant at all.** Nothing
I wrote noticed that Q4's nearest chunk is about pass/fail declarations, or that
the gate's margin for Q4 comes from that chunk. Four of my five criteria are
about whether the pipeline's plumbing works. Only one is about whether retrieval
is any good, and it was the one I wrote loosely enough to pass.

**And I would write down the expected distance, not just the expected string.**
`expects` gave me a correctness check but no sensitivity to *how* a question was
answered. Recording "Q4 should come back under 0.60 from `thread_late_work.txt`"
in unit 1 would have made the rank-4 hit a visible failure in unit 1 rather than
something I found in unit 2 by printing rankings by hand.

## How I Used AI — unit 2

**1. Arguing the opposite verdict, which found a bug rather than a verdict
error.** I pasted criterion 1, its target, my three runs and my MET verdict into
Claude and asked it to argue the opposite as strongly as it could. It did not
argue that the verdict was wrong. It asked which document the Q4 match came
from — and the answer was `thread_group_project.txt`, not the document that
holds the answer. That is the entire reason criterion 1 got revised. I had read
"contains the answer" as unambiguous for a week.

**2. Asking why my improvement might not work, before building it.** I asked
"I'm going to add BM25 hybrid search to fix Q4's ranking — tell me why that might
not work" and got the objection I then wrote into *What I expected to go wrong*:
BM25 needs shared terms and "extension" is not in the corpus. It also pointed at
Q5 as the question most likely to regress, for the same reason Q4 was failing.
Q5 did regress, from rank 1 to rank 5. Having predicted that in writing is the
difference between reporting a result and explaining one — and it is why I went
looking for the counterpoint-reply pattern instead of treating Q4 and Q5 as two
unrelated problems.

**3. Spotting the `scorer.py` bug.** I asked Claude to check why Q2 was marked
failed when the answers plainly said "16GB", and it pointed at operator
precedence in `answer or "".lower()`. I would have got there eventually, but I
had already written "generation is inconsistent on Q2" in my notes as a
diagnosis of a failure that never happened — which is a good argument for
checking your instrument before diagnosing your system.

**4. What I did not take from it.** When I asked about the `RRF_K` trade-off,
Claude suggested weighting the two rankings and tuning the weight. I ran the
sweep instead and found no value of `RRF_K` satisfies both questions, for a
structural reason. A weight would have had the same problem, and with five test
questions I would have been tuning a second parameter to fit two data points.
The sweep table above is in the README because a negative result I can show
beats a fix I cannot justify.
