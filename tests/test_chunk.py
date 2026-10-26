from policyqa.chunk import chunk_page


def test_windows_overlap_and_cover():
    words = [f"w{i}" for i in range(25)]
    out = list(chunk_page(" ".join(words), size=10, overlap=3))
    assert out[0].split()[:3] == ["w0", "w1", "w2"]
    assert out[1].split()[0] == "w7"
    assert out[-1].split()[-1] == "w24"


def test_short_page_is_one_chunk():
    assert list(chunk_page("a b c", 300, 60)) == ["a b c"]


def test_empty_page_yields_nothing():
    assert list(chunk_page("   ", 300, 60)) == []
