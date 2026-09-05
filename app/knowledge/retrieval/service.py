from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.provider import LLMProvider
from app.knowledge.models import KnowledgeArticle, KnowledgeChunk

MIN_RELEVANCE_SCORE = 0.72  # cosine-similarity threshold below which we refuse to answer from RAG


class RetrievedChunk(BaseModel):
    article_id: str
    article_title: str
    content: str
    score: float


class RAGRetrievalService:
    """Query normalization -> embedding -> vector search -> metadata
    filtering -> relevance scoring. Only approved, active, in-language
    articles are eligible. If nothing clears MIN_RELEVANCE_SCORE, the
    caller must say the info can't be verified rather than hallucinate."""

    def __init__(self, db: AsyncSession, llm: LLMProvider):
        self.db = db
        self.llm = llm

    async def retrieve(
        self, query: str, *, language: str, category: str | None = None, top_k: int = 5
    ) -> list[RetrievedChunk]:
        normalized_query = query.strip()
        [query_embedding] = await self.llm.embeddings([normalized_query])

        now = datetime.now(timezone.utc)
        conditions = [
            KnowledgeArticle.status == "active",
            KnowledgeArticle.approval_status == "approved",
            KnowledgeArticle.language == language,
            or_(KnowledgeArticle.effective_from.is_(None), KnowledgeArticle.effective_from <= now),
            or_(KnowledgeArticle.effective_to.is_(None), KnowledgeArticle.effective_to >= now),
        ]
        if category:
            conditions.append(KnowledgeArticle.category == category)

        stmt = (
            select(
                KnowledgeChunk.content,
                KnowledgeArticle.id,
                KnowledgeArticle.title,
                KnowledgeChunk.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .join(KnowledgeArticle, KnowledgeArticle.id == KnowledgeChunk.article_id)
            .where(and_(*conditions))
            .order_by("distance")
            .limit(top_k)
        )
        rows = (await self.db.execute(stmt)).all()

        results = []
        for content, article_id, title, distance in rows:
            score = 1 - distance  # cosine distance -> similarity
            if score >= MIN_RELEVANCE_SCORE:
                results.append(
                    RetrievedChunk(article_id=str(article_id), article_title=title, content=content, score=score)
                )
        return results

    def build_context_block(self, chunks: list[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        parts = [f"[{c.article_title}]\n{c.content}" for c in chunks]
        return "\n\n---\n\n".join(parts)
