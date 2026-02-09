from rag.text.chunking import chunk_text


def test_chunk_text_basic():
    text = "one two three four five six seven eight nine ten"
    chunks = chunk_text(text, chunk_size=4, overlap=1)
    assert chunks[0] == "one two three four"
    assert chunks[1].startswith("four")
    assert chunks[-1].endswith("ten")
