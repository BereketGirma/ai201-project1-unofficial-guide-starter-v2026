# Acceptance criteria — The Unofficial Guide

Five criteria that say what "working" means for this system, written in unit 1
**before** any results existed.

An acceptance criterion names a target: a number, a count, a rate, or something
a person could plainly observe. *"Retrieval works"* is an opinion. *"For at
least 4 of my 5 test questions, the top results include a chunk containing the
answer"* is a criterion.

Under each one, write a sentence or two on **why that target** and not a
stricter or looser one. A reason that says something about your corpus or your
pipeline earns credit; *"80% seemed reasonable"* does not.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

Corpus: `advice_threads` — 23 question-and-answer threads, 75 replies, replies
that disagree with each other as often as not.

---

## 1. Retrieved chunks contain the answer

For at least 4 of my 5 test questions, the retrieved chunks include one that
contains the answer.

**Why this target:**
Four of five and not five of five because Q4 ("the most reliable way to get an
extension") is the one I expect to lose. Its answer is in reply 2 of
`thread_late_work.txt`, but that thread's title asks a different question —
"what actually happens if you hand something in late?" — so the chunk's
embedding is pulled toward consequences rather than toward asking early. It
already comes back furthest of my five, and it is the question most likely to
drop out when I re-chunk. The other four sit in threads whose title and answer
point the same way, so if any of those miss, something is broken rather than
merely hard.

> **Revised in unit 2:** For at least 4 of my 5 test questions, the retrieved
> chunks include one that contains the answer **and comes from the document
> that actually holds it** (`answer_in` in `questions.py`).
>
> **Why revised:** The original could be satisfied by the wrong document, so it
> was not measuring what I meant. Q4 expects the phrase "before the deadline".
> That phrase appears in `thread_late_work.txt` — reply 2, "the universal rule:
> ask before the deadline, not after" — which is the answer. It also appears in
> `thread_group_project.txt` — reply 2, "most instructors here will adjust
> individual grades if you raise it before the deadline rather than after" —
> which is a different claim about group-project grading and answers nothing
> about extensions. When I measured criterion 1, the `group_project` chunk
> ranked second and the `late_work` chunk ranked fourth, so my check credited
> the hit to the wrong document and called it a pass. It was right by accident.
>
> This is a fix to the measurement, not to the target. The number stays at 4 of
> 5, and on the before-run the revised criterion comes out 5 of 5 exactly as the
> original did — `thread_late_work.txt#1` is in the top five, just badly ranked.
> So the verdict does not change. What changes is that the criterion can no
> longer pass for the wrong reason, which matters because the badly-ranked
> `late_work` chunk is the thing my improvement is trying to move.

---

## 2. Every answer names a source

Every answer the system produces names at least one source document.

**Why this target:**
All five and not four because nothing about this one is left to chance.
`generate.py` appends the source line from the retrieved chunks' metadata, and
the relevance gate means the model is never called with an empty context in
the first place — a question with no close chunk is refused before generation.
So the only way to land under 5 of 5 is a real defect in how sources are
carried through, and I would rather find that than excuse it.

---

## 3. The relevance gate stops out-of-corpus questions

When I ask a question my documents clearly don't cover, the relevance gate
stops it and the system returns "I don't have enough information about that" —
in at least 4 of 5 tries.

<!-- The five questions are the ones in `OUT_OF_SCOPE` at the bottom of
     `questions.py`, and `run_eval.py` puts them through the gate and writes
     what happened into your run log. Swap them for your own if you'd rather —
     just keep five of them, or the "4 of 5" above has nothing to be 4 of. -->

**Why this target:**
The two groups separated cleanly when I measured them. My five in-corpus
questions came back at 0.180, 0.330, 0.391, 0.405 and 0.591; the five
`OUT_OF_SCOPE` questions at 0.787, 0.828, 0.871, 0.890 and 0.930. That is a gap
of roughly 0.2 with nothing sitting in it, which is wide enough that I would
expect 5 of 5 today. I am still writing 4 of 5, because those numbers were
measured against the starter's whole-thread chunks, and Milestone 3 replaces
the chunker. Shorter chunks carry less text, and a chunk about bikes or laundry
may well end up closer to an unrelated question than a whole thread was. I do
not yet know which direction the gap moves, so I am leaving one slot for it to
narrow.

---

## 4. Chunks are self-contained and none is a fragment

Every chunk is between 80 and 400 characters long, and every chunk contains the
`THREAD:` question line from the document it came from. I check this by
scripting it over the full set of chunks, not by eye — both halves are
mechanical, so the answer is the same whoever runs it.

**Why this target:**
Both halves come from something I saw in the documents. The lower bound exists
because the starter chunker produces a 2-character chunk on this corpus — the
tail of a thread that did not divide evenly into 800-character windows. The
shortest actual reply in the corpus is 68 characters, and once a thread title
is prefixed the shortest possible real chunk is around 120, so an 80-character
floor cannot be satisfied by a fragment but does not force me to glue unrelated
replies together to clear it. The upper bound is 400 because the longest reply
is 195 characters and the longest title around 70; anything much past 400 means
I have merged replies that disagree with each other into one chunk, which is
the specific failure this corpus invites.

The `THREAD:` requirement is the half I actually care about. Splitting per
reply is the obvious move here, and it has an obvious cost: reply 3 of
`thread_bike_commute.txt` reads "Both true. I keep a cheap bike for September
to November and walk the rest of the year." On its own that answers nothing —
you cannot tell what is both true, or what the bike is being compared against.
Carrying the thread question into every chunk is what stops per-reply chunking
from producing text that retrieves well and means nothing. I chose a mechanical
test over "does this read as a complete thought" on purpose, because I do not
trust myself to judge that the same way twice.

---

## 5. In-corpus questions are not refused

All 5 of my test questions pass the relevance gate. None of them is refused,
measured at whatever cutoff I settle on in Milestone 4.

**Why this target:**
This is the criterion that stops me from gaming criterion 3. Refusals are easy
to get right if you refuse everything, and criterion 3 on its own rewards
pushing the cutoff down. Q4 is why that is not free: it came back at 0.591
against the shipped cutoff of 0.6, so a real question with a real answer in the
documents clears the gate by nine thousandths. Drop the cutoff to 0.55 to make
refusals look decisive and I silently start refusing a question I can answer —
and a wrong refusal is worse than a wrong answer here, because it looks like
honesty.

Five of five and not four because the gap I measured is wide enough to hold
both targets at once: putting the cutoff near 0.70 leaves every in-corpus
question roughly 0.11 of margin and every out-of-scope question roughly 0.09 on
the other side. If I cannot hit 5 of 5 and 4 of 5 together, that tells me the
gap closed when I re-chunked, and that is exactly the thing I want to find out.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 2 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath it, like this:

         ## 1. Retrieved chunks contain the answer

         For at least 4 of my 5 test questions, the retrieved chunks include
         one that contains the answer.

         **Why this target:** ...

         > **Revised in unit 2:** For at least 4 of 5 questions, the top three
         > results contain the answer.
         >
         > **Why revised:** I couldn't judge "the chunks include one that
         > contains the answer" the same way twice — I scored two questions
         > differently on Monday than on Wednesday. The new version is
         > something I can actually check.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "I said 4 of 5 but got 2 of 5, so 2 of 5 is more realistic."

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.

     The whole reason the originals stay visible is so someone can see what you
     said before you knew the answer.
     ───────────────────────────────────────────────────────────────────────── -->
