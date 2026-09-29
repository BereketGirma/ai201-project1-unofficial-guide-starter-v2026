"""
How I decide whether an answer was right.

`run_eval.py` finds `judge` automatically and uses it to fill the pass/fail
cells in the run log.

The first version of this file was one line:

    return expects.strip().lower() in (answer or "".lower())

which is wrong, and wrong in a way that is hard to see. `.lower()` binds to
`""`, not to `answer` — Python reads it as `answer or ("".lower())`. So the
answer never gets lowercased and the match is case-sensitive on one side only.
`"16gb" in "...16GB..."` is False, which marked Q2 failed on all three runs of
`results/run_2026-09-23_2020_before.md` even though every one of those answers
says "16GB". The system was right and the scorer was wrong.

That is why the baseline in this unit was re-run after the fix: a before/after
comparison measured with a broken instrument tells you nothing.

The helpers below exist because my five criteria measure five different things
and a single bool cannot carry all of them. `check_criteria.py` uses them.
"""

import re

# Source filenames in this corpus all look like `thread_something.txt`.
# Criterion 2 asks whether the answer names one; this is how I detect that.
SOURCE_PATTERN = re.compile(r"thread_[a-z_]+\.txt", re.I)


def _norm(text: str) -> str:
    """Lowercase and collapse whitespace, so matching is not tripped by either."""
    return re.sub(r"\s+", " ", (text or "").lower())


def judge(question: str, expects: str, answer: str, results) -> bool:
    """
    Did the generated answer contain what I said a correct answer would contain?

    This is the end-to-end check: retrieval and generation both had to work for
    it to come out True. `expects` is the word or phrase I wrote in
    `questions.py` in unit 1, before I had seen any output.
    """
    if not expects:
        return False
    return _norm(expects) in _norm(answer)


def contains_answer(results, expects: str, answer_in: str | None = None) -> bool:
    """
    Criterion 1 (revised in unit 2): did retrieval put the answer in front of
    the model, *from the document that actually holds it*?

    This looks at retrieved chunk text, not the generated answer, because
    criterion 1 is a claim about retrieval. An answer can be wrong while
    retrieval was fine (a generation problem) and this is what separates those
    two cases.

    `answer_in` is why the criterion was revised. Matching on `expects` alone
    let Q4 pass on a chunk from `thread_group_project.txt`, which contains the
    phrase "before the deadline" while answering a different question. Requiring
    the hit to come from the right document stops the criterion passing by
    accident.
    """
    return answer_rank(results, expects, answer_in) is not None


def answer_rank(results, expects: str, answer_in: str | None = None) -> int | None:
    """
    Where in the ranking the answer-bearing chunk landed, 1-based. None if absent.

    The rank, not just the presence, is what the unit 2 improvement is trying to
    move: on the before-run Q4's answer chunk was retrieved but sat at rank 4,
    behind two chunks that answer nothing.
    """
    if not expects:
        return None
    needle = _norm(expects)
    for rank, r in enumerate(results, 1):
        if needle not in _norm(r.text):
            continue
        if answer_in and answer_in.lower() not in r.source.lower():
            continue
        return rank
    return None


def names_source(answer: str) -> bool:
    """Criterion 2: does this answer name at least one source document?"""
    return bool(SOURCE_PATTERN.search(answer or ""))
