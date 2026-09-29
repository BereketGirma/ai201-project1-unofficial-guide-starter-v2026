#!/usr/bin/env python3
"""
Measure all five acceptance criteria and write the criterion-level run log.

    python check_criteria.py --report results/run_2026-09-27_1010_before.md --label before

`run_eval.py` produces one row per QUESTION. criteria.md names five criteria
and the README asks for one row per CRITERION, so something has to do the
aggregation. This is that something.

Why it is a separate script from run_eval.py: `judge` returns a single bool per
question per run, and my five criteria measure five different things. One bool
cannot carry all five.

What costs model calls and what does not
----------------------------------------
Only criterion 2 depends on generated text, and this script reads that from the
run_eval report rather than regenerating it — so the criterion table is derived
from the same committed evidence a grader can read, and running this script
costs zero model calls.

  1. Answer retrieved from the right doc  — retrieval only, deterministic
  2. Every answer names a source          — parsed from the report's answers
  3. Gate stops out-of-corpus questions   — retrieval + gate, deterministic
  4. Chunks 80-400 chars, carry THREAD:   — the chunker, deterministic
  5. No in-corpus question refused        — retrieval + gate, deterministic

Criteria 1, 3, 4 and 5 come out identical in all three run columns, and that is
correct rather than lazy: embedding a question is deterministic, the gate is a
comparison against a fixed number, and the chunker is a pure function of the
documents. Criterion 2 is the only one that can move between runs, because it
is the only one that depends on what the model wrote.
"""

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

import config
import questions as qs
import scorer

# "### <question> — run 2" — the heading run_eval.py writes per answer.
ANSWER_HEADING = re.compile(r"^### (?P<question>.+?) — run (?P<run>\d+)\s*$", re.M)


def parse_report(path: Path) -> dict[int, list[str]]:
    """
    Pull the generated answers out of a run_eval.py report, keyed by run number.

    The report's "Real output" section is one `###` heading per question per
    run, followed by a fenced block holding the answer text. That is the only
    place the answers exist, and criterion 2 is a claim about them.
    """
    text = path.read_text(encoding="utf-8")
    by_run: dict[int, list[str]] = {}

    matches = list(ANSWER_HEADING.finditer(text))
    if not matches:
        raise SystemExit(
            f"Found no '### <question> — run N' headings in {path}.\n"
            "Is that a report written by run_eval.py?"
        )

    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.end() : end]

        fence = re.search(r"```\n(?P<body>.*?)\n```", block, re.S)
        if not fence:
            continue
        run = int(match.group("run"))
        by_run.setdefault(run, []).append(fence.group("body"))

    return by_run


def criterion_1(top_k, corpus, variant):
    """
    For how many questions do the retrieved chunks contain the answer, from the
    document that actually holds it?

    This is criterion 1 as revised in unit 2. The `answer_in` check is the
    revision: matching on `expects` alone credited Q4 to a chunk from
    `thread_group_project.txt`, which carries the phrase "before the deadline"
    while answering a different question.
    """
    from store import search

    hits, detail = 0, []
    for item in qs.answered():
        results = search(item["question"], top_k=top_k, corpus=corpus, variant=variant)
        expects = item.get("expects", "")
        answer_in = item.get("answer_in")

        rank = scorer.answer_rank(results, expects, answer_in)
        loose = scorer.answer_rank(results, expects, None)
        hits += rank is not None

        detail.append({
            "question": item["question"],
            "expects": expects,
            "answer_in": answer_in or "—",
            "rank": rank,
            "loose_rank": loose,
            "found_in": next(
                (r.label for r in results if scorer.answer_rank([r], expects, answer_in)),
                "—",
            ),
            "top_source": results[0].label if results else "—",
            "best": min((r.distance for r in results), default=1.0),
        })
    return hits, detail


def criterion_2(by_run):
    """In how many answers per run is a source document named?"""
    counts, detail = {}, []
    for run in sorted(by_run):
        answers = by_run[run]
        named = [scorer.names_source(a) for a in answers]
        counts[run] = (sum(named), len(named))
        for answer, ok in zip(answers, named):
            if not ok:
                detail.append({"run": run, "answer": answer})
    return counts, detail


def criterion_3(top_k, threshold, corpus, variant):
    """How many out-of-corpus questions does the gate refuse?"""
    from store import search
    import gate

    refused, detail = 0, []
    for question in getattr(qs, "OUT_OF_SCOPE", []):
        results = search(question, top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        refused += not decision.passed
        detail.append({
            "question": question,
            "refused": not decision.passed,
            "best": decision.best_distance,
        })
    return refused, detail


def criterion_4():
    """Is every chunk 80-400 characters and carrying its THREAD: line?"""
    from chunker import split_documents
    from ingest import load_documents

    chunks = split_documents(load_documents())
    good, bad = 0, []
    for chunk in chunks:
        length_ok = 80 <= len(chunk.text) <= config.MAX_CHUNK_CHARS
        thread_ok = "THREAD:" in chunk.text
        if length_ok and thread_ok:
            good += 1
        else:
            bad.append({
                "label": chunk.label,
                "length": len(chunk.text),
                "length_ok": length_ok,
                "thread_ok": thread_ok,
            })
    return good, len(chunks), bad


def criterion_5(top_k, threshold, corpus, variant):
    """How many of my own five questions clear the gate?"""
    from store import search
    import gate

    passed, detail = 0, []
    for item in qs.answered():
        results = search(item["question"], top_k=top_k, corpus=corpus, variant=variant)
        decision = gate.check(results, threshold=threshold)
        passed += decision.passed
        detail.append({
            "question": item["question"],
            "passed": decision.passed,
            "best": decision.best_distance,
        })
    return passed, detail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True,
                        help="the run_eval.py report holding the generated answers")
    parser.add_argument("--label", default="", help="e.g. before / after")
    parser.add_argument("--corpus", default=None)
    parser.add_argument("--variant", default="default")
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    corpus = args.corpus or config.CORPUS
    top_k = args.top_k or config.TOP_K
    threshold = config.THRESHOLD if args.threshold is None else args.threshold

    report = Path(args.report)
    if not report.exists():
        raise SystemExit(f"No such report: {report}")

    by_run = parse_report(report)
    n_runs = len(by_run)
    n_questions = len(qs.answered())

    c1, c1_detail = criterion_1(top_k, corpus, args.variant)
    c2, c2_detail = criterion_2(by_run)
    c3, c3_detail = criterion_3(top_k, threshold, corpus, args.variant)
    c4_good, c4_total, c4_bad = criterion_4()
    c5, c5_detail = criterion_5(top_k, threshold, corpus, args.variant)

    def verdict(ok: bool) -> str:
        return "MET" if ok else "MISSED"

    n_oos = len(getattr(qs, "OUT_OF_SCOPE", []))
    runs = sorted(by_run)

    # Targets are the ones written in criteria.md in unit 1. Not new ones.
    rows = [
        ("1. Retrieved chunk contains the answer (revised)", "4 of 5",
         [f"{c1}/{n_questions}"] * n_runs, verdict(c1 >= 4)),
        ("2. Every answer names a source", "5 of 5",
         [f"{c2[r][0]}/{c2[r][1]}" for r in runs],
         verdict(all(c2[r][0] == c2[r][1] for r in runs))),
        ("3. Gate stops out-of-corpus questions", "4 of 5",
         [f"{c3}/{n_oos}"] * n_runs, verdict(c3 >= 4)),
        ("4. Chunks 80-400 chars and carry a THREAD: line", f"all {c4_total}",
         [f"{c4_good}/{c4_total}"] * n_runs, verdict(not c4_bad)),
        ("5. No in-corpus question refused", "5 of 5",
         [f"{c5}/{n_questions}"] * n_runs, verdict(c5 == n_questions)),
    ]

    header = " | ".join(f"Run {r}" for r in runs)
    divider = "|".join(["---"] * n_runs)

    lines = [
        f"# Criterion run log{f' — {args.label}' if args.label else ''}",
        "",
        f"- Produced by: `check_criteria.py::main`",
        f"- Answers read from: `{report.name}` (written by `run_eval.py::main`)",
        f"- Corpus: `{corpus}` (index variant `{args.variant}`)",
        f"- top-k: {top_k} · relevance cutoff: {threshold}",
        f"- When: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Targets are the ones written in `criteria.md` in unit 1, unchanged.",
        "",
        f"| Criterion | Target | {header} | Verdict |",
        f"|---|---|{divider}|---|",
    ]
    for name, target, cells, call in rows:
        lines.append(f"| {name} | {target} | {' | '.join(cells)} | {call} |")

    lines += [
        "",
        "Criteria 1, 3, 4 and 5 are identical across the three run columns because",
        "each is deterministic: embedding a question returns the same vector every",
        "time, the gate is a comparison against a fixed number, and the chunker is a",
        "pure function of the documents. Criterion 2 is the only one that can move,",
        "because it is the only one that depends on what the model wrote.",
        "",
        "---",
        "",
        "## Criterion 1 — where the answer was found",
        "",
        "Produced by `check_criteria.py::criterion_1` via `scorer.py::answer_rank`, which",
        "looks at retrieved chunk text rather than the generated answer, and requires the",
        "hit to come from the document named in `answer_in` — the unit 2 revision.",
        "",
        "| Question | Expects | Answer lives in | Found at rank | Which chunk | Top-1 chunk | Best distance |",
        "|---|---|---|---|---|---|---|",
    ]
    for d in c1_detail:
        rank = f"{d['rank']}" if d["rank"] else "**not retrieved**"
        if d["rank"] and d["loose_rank"] and d["loose_rank"] != d["rank"]:
            rank += f" (loose check said {d['loose_rank']})"
        lines.append(
            f"| {d['question']} | `{d['expects']}` | `{d['answer_in']}` | {rank} | "
            f"`{d['found_in']}` | `{d['top_source']}` | {d['best']:.3f} |"
        )

    lines += [
        "",
        "## Criterion 2 — answers that named no source",
        "",
        "Produced by `check_criteria.py::criterion_2` via `scorer.py::names_source`.",
        "",
    ]
    if c2_detail:
        for d in c2_detail:
            lines += [f"Run {d['run']}:", "", "```", d["answer"], "```", ""]
    else:
        lines += ["Every answer in every run named at least one source document.", ""]

    lines += [
        "## Criterion 3 — the gate on out-of-corpus questions",
        "",
        f"Produced by `check_criteria.py::criterion_3`, cutoff {threshold}. "
        f"Refused {c3} of {n_oos}.",
        "",
        "| Out-of-scope question | Best distance | Gate |",
        "|---|---|---|",
    ]
    for d in c3_detail:
        lines.append(
            f"| {d['question']} | {d['best']:.3f} | "
            f"{'refused' if d['refused'] else '**let through**'} |"
        )

    lines += [
        "",
        "## Criterion 4 — chunk shape",
        "",
        f"Produced by `check_criteria.py::criterion_4` over all {c4_total} chunks from "
        f"`chunker.py::split_documents`. {c4_good} of {c4_total} are between 80 and "
        f"{config.MAX_CHUNK_CHARS} characters and contain a `THREAD:` line.",
        "",
    ]
    if c4_bad:
        lines += ["| Chunk | Length | 80-400? | Has THREAD:? |", "|---|---|---|---|"]
        for d in c4_bad:
            lines.append(
                f"| `{d['label']}` | {d['length']} | "
                f"{'yes' if d['length_ok'] else '**no**'} | "
                f"{'yes' if d['thread_ok'] else '**no**'} |"
            )
        lines.append("")
    else:
        lines += ["No chunk violates either half of the criterion.", ""]

    lines += [
        "## Criterion 5 — my own questions against the gate",
        "",
        f"Produced by `check_criteria.py::criterion_5`, cutoff {threshold}. "
        f"Passed {c5} of {n_questions}.",
        "",
        "| Question | Best distance | Gate |",
        "|---|---|---|",
    ]
    for d in c5_detail:
        lines.append(
            f"| {d['question']} | {d['best']:.3f} | "
            f"{'passed' if d['passed'] else '**refused**'} |"
        )

    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    label = f"_{args.label}" if args.label else ""
    out = config.RESULTS_DIR / f"criteria_{stamp}{label}.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\n| Criterion | Target | {header} | Verdict |")
    print(f"|---|---|{divider}|---|")
    for name, target, cells, call in rows:
        print(f"| {name} | {target} | {' | '.join(cells)} | {call} |")
    print(f"\nWrote {out.relative_to(config.ROOT)}")


if __name__ == "__main__":
    main()
