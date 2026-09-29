"""
Your test questions.

Milestone 2 asks you to write five questions your system should be able to
answer from your corpus, specific enough to have a right answer.

  ✗ "What are good dining halls?"          — no right answer
  ✓ "What do students say about wait times at Commons during lunch?"

Fill in `QUESTIONS` below. `expects` is a word or short phrase you'd expect a
correct answer to contain — you'll use it in unit 2 when you build a scorer,
and having written it now means you decided what "correct" meant before you saw
any results.

`answer_in` names the document that actually holds the answer. It was added in
unit 2 because criterion 1 was revised: `expects` alone is not enough to check
that criterion honestly. "before the deadline" appears in both
`thread_late_work.txt` (the real answer to Q4) and `thread_group_project.txt`
(a different claim about group-project grades), so a bare substring match
credited Q4 to the wrong document. `answer_in` is the ground truth that makes
the revised criterion mechanical.

`OUT_OF_SCOPE` holds five questions your documents clearly don't cover. You
need these in Milestone 4 to find where your relevance cutoff belongs, and
again in unit 2, where `run_eval.py` runs them through the gate and writes what
happened into your run log — that's the evidence for criterion 3.

Swap them for your own if you like. Keep five of them either way: criterion 3
names a target of "4 of 5", and four of three is not a thing.
"""

# Five questions about advice_threads, ordered roughly easiest to hardest.
#
# Q1-Q2 have their answer sitting in a single reply, stated as a number.
# Q3's answer is conditional and buried mid-sentence in one reply.
# Q4's answer is a norm rather than a number, and the reply that carries it
#   is not the top-voted reply in the thread.
# Q5 is the hard one on purpose: the four replies in thread_bike_commute.txt
#   disagree with each other, so a correct answer has to pick up the winter
#   objection rather than just the first enthusiastic reply.
QUESTIONS = [
    {
        "question": "How many black-and-white pages does the printing quota cover?",
        "expects": "600",
        "answer_in": "thread_printing.txt",
    },
    {
        "question": "How much RAM do students say is worth paying for on a laptop for CS courses?",
        "expects": "16GB",
        "answer_in": "thread_laptop_specs.txt",
    },
    {
        "question": "If a syllabus doesn't state an email response window, how long should I wait before following up with a professor?",
        "expects": "48 hours",
        "answer_in": "thread_professor_email.txt",
    },
    {
        "question": "What is the most reliable way to get an extension on a late assignment?",
        "expects": "before the deadline",
        "answer_in": "thread_late_work.txt",
    },
    {
        "question": "Do students recommend keeping a bike through the winter here?",
        "expects": "salt",
        "answer_in": "thread_bike_commute.txt",
    },
]

# Questions from a different world entirely. Your gate should refuse all five.
#
# There are five of these because criterion 3 in criteria.md names a target of
# "at least 4 of 5" — you need five things to try before you can report 4 of 5.
# `run_eval.py` runs these through retrieval and the gate on every eval and
# records what happened, so criterion 3 has evidence in the run log alongside
# the others. They cost no model calls: a refusal never reaches the model.
OUT_OF_SCOPE = [
    "What is the capital of Mongolia?",
    "How do I change the oil in a diesel engine?",
    "Who won the 1994 World Cup?",
    "What is the recommended dosage of ibuprofen for a headache?",
    "How do I write a for loop in Rust?",
]


def answered() -> list[dict]:
    """The questions you've actually filled in."""
    return [q for q in QUESTIONS if q.get("question", "").strip()]
