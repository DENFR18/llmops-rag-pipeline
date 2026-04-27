from pathlib import Path

from llama_index.core import Document

from src.config import Settings
from src.ingest import chunk_documents, load_documents


def test_load_documents_reads_markdown(tmp_path: Path):
    (tmp_path / "a.md").write_text("# Hello\nworld", encoding="utf-8")
    (tmp_path / "ignored.txt").write_text("nope", encoding="utf-8")
    sub = tmp_path / "nested"
    sub.mkdir()
    (sub / "b.md").write_text("nested content", encoding="utf-8")

    docs = load_documents(tmp_path)

    assert len(docs) == 2
    sources = {d.metadata["source"] for d in docs}
    assert sources == {"a.md", "nested/b.md"}


def test_chunk_documents_produces_overlapping_nodes():
    settings = Settings(rag_chunk_size=64, rag_chunk_overlap=16)
    long_text = " ".join(["lorem ipsum dolor sit amet"] * 200)
    docs = [Document(text=long_text, metadata={"source": "long.md"})]

    nodes = chunk_documents(docs, settings)

    assert len(nodes) > 1
    assert all(node.metadata.get("source") == "long.md" for node in nodes)


def test_chunk_documents_empty_input_yields_no_nodes():
    settings = Settings()
    assert chunk_documents([], settings) == []
