from dataclasses import dataclass

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

from src.config import Settings, get_settings
from src.ingest import _load_embedding_model, build_vector_store


@dataclass
class RetrievedChunk:
    text: str
    source: str
    score: float


class Retriever:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        vector_store = build_vector_store(self.settings)
        embed_model = _load_embedding_model(self.settings)
        index = VectorStoreIndex.from_vector_store(vector_store, embed_model=embed_model)
        self._retriever = index.as_retriever(similarity_top_k=self.settings.rag_top_k)

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        nodes: list[NodeWithScore] = self._retriever.retrieve(query)
        return [
            RetrievedChunk(
                text=n.node.get_content(),
                source=n.node.metadata.get("source", "unknown"),
                score=float(n.score or 0.0),
            )
            for n in nodes
        ]


def format_context(chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "(no context available)"
    return "\n\n".join(
        f"[{i + 1}] source={c.source} score={c.score:.3f}\n{c.text}"
        for i, c in enumerate(chunks)
    )
