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

<!-- These sections get ADDED to what's already above. Don't delete or rewrite
     unit 1 — the point is that someone can see what you said before you knew
     how it went. -->

## Run Log — Before

<!-- Your five criteria, three runs each. `python run_eval.py --label before`
     runs the questions, puts the OUT_OF_SCOPE ones through the gate, and
     writes it all into results/ for you. Targets come from criteria.md; the
     verdict column is your call.

     Criterion 3 is measured in one deterministic pass rather than three, so
     the same number goes in all three run columns. That's correct, not lazy.

     Milestone 1. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. Chunks 80-400 chars and carry a THREAD: line | all 75 |  |  |  |  |
| 5. No in-corpus question refused | 5 of 5 |  |  |  |  |

<!-- Underneath, paste the REAL output for each criterion from one of your
     runs — the actual text your system produced, not a description of it.
     Name the file and function that produced it. -->

## Verdicts

<!-- MET or MISSED for each of the five, against the target you wrote last
     unit — not a new one. Plus a sentence on how you decided. That sentence
     matters most where it was close.

     If your target said 4 of 5 and your runs came out 4, 3, 4, that's a MISS.
     The target has to hold, not show up occasionally.

     Milestone 2. -->

| # | Criterion | Verdict | How I decided |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

## Diagnoses

<!-- For each miss: which stage caused it, and how. The stage alone isn't
     enough — you need the mechanism.

     Not a diagnosis: "Question 3 didn't work."
     A diagnosis:     "Question 3 asks about laundry costs. The answer is in
                       one sentence that got split across two chunks, so
                       neither chunk on its own contains it."

     The five stages: loading → chunking → embedding → retrieval → generation.

     Look for a pattern. If three misses all ask about numbers, that's one
     problem, not three.

     Missed nothing? Say so, then say honestly whether your targets were set
     low, and which one you'd tighten and to what.

     Milestone 3. -->

## The Improvement

**What I changed:**

**Why I picked it:**

<!-- Connect it to a specific diagnosis above in one sentence. If you can't,
     you picked a fix because it sounded impressive. -->

### Run Log — After

<!-- Same format, same five criteria, three runs each.
     `python run_eval.py --label after` -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer | 4 of 5 |  |  |  |  |
| 2. Every answer names a source | 5 of 5 |  |  |  |  |
| 3. Gate stops out-of-corpus questions | 4 of 5 |  |  |  |  |
| 4. Chunks 80-400 chars and carry a THREAD: line | all 75 |  |  |  |  |
| 5. No in-corpus question refused | 5 of 5 |  |  |  |  |

**Did it help?**

<!-- Say plainly whether it did, and how you know. If it made things worse,
     say that — a change that backfired, honestly reported, earns full credit
     and is more interesting than one that worked. What matters is that you can
     tell.

     Milestone 4. -->

## What's Still Broken

<!-- For each criterion still missed after your fix: what you'd do about it,
     and why you stopped where you did.

     "I ran out of time" is fine if it's true. Pretending nothing is left is
     not.

     Milestone 5. -->

## What I'd Do Differently

<!-- Knowing what you know now — which of your five criteria would you write
     differently, and why?

     Milestone 5. -->
