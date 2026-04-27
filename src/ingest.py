from pathlib import Path

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import BaseNode
from llama_index.vector_stores.postgres import PGVectorStore

from src.config import Settings, get_settings


def _load_embedding_model(settings: Settings):
    if settings.embeddings_provider == "voyage":
        from llama_index.embeddings.voyageai import VoyageEmbedding

        return VoyageEmbedding(
            voyage_api_key=settings.voyage_api_key,
            model_name=settings.voyage_model,
        )
    from llama_index.embeddings.openai import OpenAIEmbedding

    return OpenAIEmbedding(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    )


def build_vector_store(settings: Settings | None = None) -> PGVectorStore:
    s = settings or get_settings()
    async_url = s.neon_database_url.replace("postgresql://", "postgresql+asyncpg://")
    return PGVectorStore.from_params(
        connection_string=s.neon_database_url,
        async_connection_string=async_url,
        table_name=s.pgvector_table,
        embed_dim=s.pgvector_dim,
    )


def load_documents(source_dir: Path) -> list[Document]:
    docs: list[Document] = []
    for path in sorted(source_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.append(Document(text=text, metadata={"source": str(path.relative_to(source_dir))}))
    return docs


def chunk_documents(docs: list[Document], settings: Settings | None = None) -> list[BaseNode]:
    s = settings or get_settings()
    splitter = SentenceSplitter(chunk_size=s.rag_chunk_size, chunk_overlap=s.rag_chunk_overlap)
    return splitter.get_nodes_from_documents(docs)


def ingest(source_dir: Path, settings: Settings | None = None) -> int:
    s = settings or get_settings()
    docs = load_documents(source_dir)
    if not docs:
        return 0
    nodes = chunk_documents(docs, s)
    vector_store = build_vector_store(s)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    embed_model = _load_embedding_model(s)
    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
    )
    return len(nodes)


if __name__ == "__main__":
    import sys

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/sample_docs")
    n = ingest(target)
    print(f"Ingested {n} chunks from {target}")
