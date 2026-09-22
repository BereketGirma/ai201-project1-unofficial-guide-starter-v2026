"""
Stage 2 of the pipeline: splitting documents into chunks.

`split_documents` cuts one chunk per reply and prefixes every chunk with the
thread's question line. `fallback_split` below it is the starter's original
fixed-window chunker, kept for comparison — Milestone 3's stop rule points back
at it, and unit 2 wants a baseline to measure against.

Why per reply, for `advice_threads`:

Every document here is one thread — a `THREAD:` question followed by two to
five replies that argue with each other. The reply is the unit of meaning: one
person's take, start to finish. The fixed-window chunker ignores that
completely. On this corpus it produced 26 chunks from 23 documents, which
means it mostly left whole threads intact and then, on the few documents that
overran 800 characters, cut them at an arbitrary character — once leaving a
2-character chunk that is the tail of a sentence and matches nothing.

Both of those are wrong in the same way. A whole thread is four disagreeing
answers embedded as one vector, so it matches every question about that topic
a little and none of them well. An arbitrary slice is worse.

The cost of splitting per reply is context. Reply 3 of thread_bike_commute.txt
reads "Both true. I keep a cheap bike for September to November and walk the
rest of the year." Alone, that answers nothing — you cannot tell what is both
true. So every chunk carries the thread question with it. That repeated
question line is this chunker's version of overlap: neighbouring chunks share
context, but the shared context is the thing that makes the reply legible
rather than an arbitrary tail of the previous window.
"""

import re
from dataclasses import dataclass

import config
from ingest import Document


@dataclass
class Chunk:
    """One piece of one document."""

    text: str
    source: str        # which file it came from
    index: int         # which chunk within that file, starting at 0
    produced_by: str   # the function that made it — cite this in your README

    @property
    def label(self) -> str:
        return f"{self.source}#{self.index}"


# "--- reply 2 (21 votes) ---" — the boundary every document in this corpus uses.
REPLY_MARKER = re.compile(r"^---\s*reply\s+\d+\s*\(\d+\s+votes\)\s*---\s*$", re.M)

# The thread's question, always the first line.
TITLE_LINE = re.compile(r"^THREAD:.*$", re.M)


def fallback_split(
    documents: list[Document],
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[Chunk]:
    """
    The starter's original chunker. Fixed-size character windows with overlap.

    Keep this function. Milestone 3's stop rule points back at it, and having
    something to compare your own strategy against is useful in unit 2.
    """
    chunk_size = chunk_size or config.CHUNK_SIZE
    overlap = overlap or config.CHUNK_OVERLAP

    if overlap >= chunk_size:
        raise ValueError("overlap has to be smaller than chunk_size")

    chunks: list[Chunk] = []
    for doc in documents:
        start = 0
        index = 0
        while start < len(doc.text):
            piece = doc.text[start : start + chunk_size].strip()
            if piece:
                chunks.append(
                    Chunk(
                        text=piece,
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::fallback_split",
                    )
                )
                index += 1
            start += chunk_size - overlap

    return chunks


def _split_oversized(body: str, budget: int) -> list[str]:
    """
    Last resort for a reply too long to fit the chunk ceiling with its title.

    No reply in `advice_threads` reaches this — the longest is 195 characters
    and the budget is comfortably above that. It exists so the length bound in
    criterion 4 holds by construction rather than by luck, and so the chunker
    does not silently break on a corpus with longer replies.
    """
    overlap = min(config.CHUNK_OVERLAP, budget // 4)
    pieces: list[str] = []
    start = 0
    while start < len(body):
        piece = body[start : start + budget].strip()
        if piece:
            pieces.append(piece)
        start += budget - overlap
    return pieces


def split_documents(documents: list[Document]) -> list[Chunk]:
    """
    One chunk per reply, each carrying its thread's question line.

    Falls back to `fallback_split` for any document that does not look like a
    thread, so bringing in documents with a different shape degrades instead of
    crashing.
    """
    chunks: list[Chunk] = []
    unstructured: list[Document] = []

    for doc in documents:
        title_match = TITLE_LINE.search(doc.text)
        replies = REPLY_MARKER.split(doc.text)

        # parts[0] is everything before the first reply — the title line.
        # Anything without both a title and at least one reply is not a thread.
        if not title_match or len(replies) < 2:
            unstructured.append(doc)
            continue

        title = title_match.group(0).strip()
        budget = config.MAX_CHUNK_CHARS - len(title) - 2

        index = 0
        for reply in replies[1:]:
            body = reply.strip()
            if not body:
                continue
            for piece in _split_oversized(body, budget):
                chunks.append(
                    Chunk(
                        text=f"{title}\n\n{piece}",
                        source=doc.source,
                        index=index,
                        produced_by="chunker.py::split_documents",
                    )
                )
                index += 1

    if unstructured:
        chunks.extend(fallback_split(unstructured))

    return chunks


def describe(chunks: list[Chunk]) -> str:
    """A one-line summary, printed after indexing."""
    if not chunks:
        return "0 chunks"
    lengths = [len(c.text) for c in chunks]
    return (
        f"{len(chunks)} chunks, "
        f"{sum(lengths) // len(lengths)} characters on average "
        f"(shortest {min(lengths)}, longest {max(lengths)}), "
        f"produced by {chunks[0].produced_by}"
    )


if __name__ == "__main__":
    from ingest import load_documents

    chunks = split_documents(load_documents())
    print(describe(chunks))
