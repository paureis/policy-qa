from policyqa.textnorm import norm, quote_overlap, tokens


def test_norm_collapses_whitespace_and_quotes():
    assert norm("A  b\n\tc “d”") == 'a b c "d"'


def test_quote_overlap_verbatim_is_one():
    q = "the provider must submit the claim within 12 months"
    assert quote_overlap(q, "Header\n   The provider  must submit\nthe claim within 12 months of service.") == 1.0


def test_quote_overlap_partial():
    q = "one two three four five six seven eight nine ten"
    text = "zero one two three four five six seven X nine ten"
    v = quote_overlap(q, text)
    assert 0.3 < v < 0.8


def test_tokens_drop_stopwords():
    assert tokens("The claim is for the provider") == ["claim", "provider"]
