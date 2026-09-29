# Criterion run log — before

- Produced by: `check_criteria.py::main`
- Answers read from: `run_2026-09-27_1544_before.md` (written by `run_eval.py::main`)
- Corpus: `advice_threads` (index variant `default`)
- top-k: 5 · relevance cutoff: 0.7
- When: 2026-09-27 15:48

Targets are the ones written in `criteria.md` in unit 1, unchanged.

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Retrieved chunk contains the answer (revised) | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 2. Every answer names a source | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 3. Gate stops out-of-corpus questions | 4 of 5 | 5/5 | 5/5 | 5/5 | MET |
| 4. Chunks 80-400 chars and carry a THREAD: line | all 75 | 75/75 | 75/75 | 75/75 | MET |
| 5. No in-corpus question refused | 5 of 5 | 5/5 | 5/5 | 5/5 | MET |

Criteria 1, 3, 4 and 5 are identical across the three run columns because
each is deterministic: embedding a question returns the same vector every
time, the gate is a comparison against a fixed number, and the chunker is a
pure function of the documents. Criterion 2 is the only one that can move,
because it is the only one that depends on what the model wrote.

---

## Criterion 1 — where the answer was found

Produced by `check_criteria.py::criterion_1` via `scorer.py::answer_rank`, which
looks at retrieved chunk text rather than the generated answer, and requires the
hit to come from the document named in `answer_in` — the unit 2 revision.

| Question | Expects | Answer lives in | Found at rank | Which chunk | Top-1 chunk | Best distance |
|---|---|---|---|---|---|---|
| How many black-and-white pages does the printing quota cover? | `600` | `thread_printing.txt` | 1 | `thread_printing.txt#0` | `thread_printing.txt#0` | 0.310 |
| How much RAM do students say is worth paying for on a laptop for CS courses? | `16GB` | `thread_laptop_specs.txt` | 1 | `thread_laptop_specs.txt#0` | `thread_laptop_specs.txt#0` | 0.129 |
| If a syllabus doesn't state an email response window, how long should I wait before following up with a professor? | `48 hours` | `thread_professor_email.txt` | 1 | `thread_professor_email.txt#0` | `thread_professor_email.txt#0` | 0.202 |
| What is the most reliable way to get an extension on a late assignment? | `before the deadline` | `thread_late_work.txt` | 4 (loose check said 2) | `thread_late_work.txt#1` | `thread_first_year_regret.txt#1` | 0.589 |
| Do students recommend keeping a bike through the winter here? | `salt` | `thread_bike_commute.txt` | 1 | `thread_bike_commute.txt#1` | `thread_bike_commute.txt#1` | 0.443 |

## Criterion 2 — answers that named no source

Produced by `check_criteria.py::criterion_2` via `scorer.py::names_source`.

Every answer in every run named at least one source document.

## Criterion 3 — the gate on out-of-corpus questions

Produced by `check_criteria.py::criterion_3`, cutoff 0.7. Refused 5 of 5.

| Out-of-scope question | Best distance | Gate |
|---|---|---|
| What is the capital of Mongolia? | 0.899 | refused |
| How do I change the oil in a diesel engine? | 0.905 | refused |
| Who won the 1994 World Cup? | 0.898 | refused |
| What is the recommended dosage of ibuprofen for a headache? | 0.819 | refused |
| How do I write a for loop in Rust? | 0.861 | refused |

## Criterion 4 — chunk shape

Produced by `check_criteria.py::criterion_4` over all 75 chunks from `chunker.py::split_documents`. 75 of 75 are between 80 and 400 characters and contain a `THREAD:` line.

No chunk violates either half of the criterion.

## Criterion 5 — my own questions against the gate

Produced by `check_criteria.py::criterion_5`, cutoff 0.7. Passed 5 of 5.

| Question | Best distance | Gate |
|---|---|---|
| How many black-and-white pages does the printing quota cover? | 0.310 | passed |
| How much RAM do students say is worth paying for on a laptop for CS courses? | 0.129 | passed |
| If a syllabus doesn't state an email response window, how long should I wait before following up with a professor? | 0.202 | passed |
| What is the most reliable way to get an extension on a late assignment? | 0.589 | passed |
| Do students recommend keeping a bike through the winter here? | 0.443 | passed |
