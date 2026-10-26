"""Text normalization shared by the chunker, the retriever, and the scorer.

norm() is the same rule the golden-set verifier uses, so a gold_quote that the
verifier found on a page is found again in the chunk that holds that page text.
"""
import re

_PUNCT = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.translate(_PUNCT)).strip().lower()


_TOKEN = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")

STOP = set(
    """a an the and or of to in on for by with at from as is are was were be been being this that these those
    it its into than then there their they them which what when where who whom whose will would shall should can
    could may might must not no nor do does did done have has had having such any all each other""".split()
)


def tokens(s: str, drop_stop: bool = True) -> list[str]:
    toks = _TOKEN.findall(norm(s))
    return [t for t in toks if t not in STOP] if drop_stop else toks


def shingles(words: list[str], n: int = 4) -> set[tuple[str, ...]]:
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def quote_overlap(quote: str, text: str, n: int = 4) -> float:
    """Fraction of the quote's word n-grams present in text, 1.0 on a verbatim match.

    Both strings are whitespace-normalized first. The golden-set rule is: a chunk
    counts as holding the quote when this is at least 0.8.
    """
    nq, nt = norm(quote), norm(text)
    if not nq:
        return 0.0
    if nq in nt:
        return 1.0
    qw = _TOKEN.findall(nq)
    tw = _TOKEN.findall(nt)
    qs = shingles(qw, n)
    if not qs:
        return 0.0
    ts = shingles(tw, n)
    return len(qs & ts) / len(qs)
