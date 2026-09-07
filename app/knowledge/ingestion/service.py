import uuid

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.provider import LLMProvider
from app.core.logging import get_logger
from app.knowledge.ingestion.chunker import chunk_text
from app.knowledge.models import KnowledgeArticle, KnowledgeChunk

logger = get_logger(__name__)

EMBEDDING_BATCH_SIZE = 16


class KnowledgeIngestionService:
    """Turns an approved KnowledgeArticle's raw content into searchable,
    embedded chunks. Re-running ingestion on an article replaces its old
    chunks so edits don't leave stale vectors behind."""

    def __init__(self, db: AsyncSession, embedding_provider: LLMProvider):
        self.db = db
        self.embedding_provider = embedding_provider

    async def ingest_article(self, article: KnowledgeArticle) -> int:
        chunks = chunk_text(article.content)
        if not chunks:
            logger.warning("ingestion_no_chunks_produced", article_id=str(article.id))
            return 0

        # Replace any existing chunks for this article (handles re-ingestion after edits)
        await self.db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.article_id == article.id))

        embeddings: list[list[float]] = []
        for i in range(0, len(chunks), EMBEDDING_BATCH_SIZE):
            batch = chunks[i : i + EMBEDDING_BATCH_SIZE]
            embeddings.extend(await self.embedding_provider.embeddings(batch))

        for index, (content, embedding) in enumerate(zip(chunks, embeddings)):
            self.db.add(
                KnowledgeChunk(article_id=article.id, chunk_index=index, content=content, embedding=embedding)
            )

        await self.db.flush()
        logger.info("ingestion_complete", article_id=str(article.id), chunk_count=len(chunks))
        return len(chunks)

    async def ingest_article_by_id(self, article_id: uuid.UUID) -> int:
        article = await self.db.get(KnowledgeArticle, article_id)
        if article is None:
            raise ValueError(f"Article {article_id} not found")
        return await self.ingest_article(article)

    async def reingest_all_active(self) -> dict[str, int]:
        """Bulk re-embed every approved/active article -- useful after
        switching embedding models (dimensions must match KnowledgeChunk.embedding)."""
        from sqlalchemy import select

        result = await self.db.execute(
            select(KnowledgeArticle).where(
                KnowledgeArticle.status == "active", KnowledgeArticle.approval_status == "approved"
            )
        )
        articles = result.scalars().all()
        counts = {}
        for article in articles:
            counts[str(article.id)] = await self.ingest_article(article)
        return counts