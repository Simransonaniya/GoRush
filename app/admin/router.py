import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.common.enums.chat import UserRole
from app.database.session import get_db
from app.knowledge.embeddings.provider import get_embedding_provider
from app.knowledge.ingestion.service import KnowledgeIngestionService
from app.knowledge.models import KnowledgeArticle

router = APIRouter(
    prefix="/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)


class KnowledgeArticleCreate(BaseModel):
    title: str
    content: str
    category: str
    language: str
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class KnowledgeArticleApprove(BaseModel):
    approve: bool


@router.get("/chat/knowledge")
async def list_knowledge(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KnowledgeArticle).order_by(KnowledgeArticle.created_at.desc()))
    articles = result.scalars().all()
    return {
        "success": True,
        "data": [
            {
                "id": str(a.id), "title": a.title, "category": a.category,
                "language": a.language, "status": a.status, "approval_status": a.approval_status,
                "version": a.version,
            }
            for a in articles
        ],
    }


@router.post("/chat/knowledge")
async def create_knowledge_article(payload: KnowledgeArticleCreate, db: AsyncSession = Depends(get_db)):
    """Creates a draft article. Embedding + chunking + approval happen via
    the knowledge/ingestion pipeline before it becomes eligible for RAG."""
    article = KnowledgeArticle(
        title=payload.title, content=payload.content, category=payload.category,
        language=payload.language, status="draft", approval_status="pending",
        effective_from=payload.effective_from, effective_to=payload.effective_to,
    )
    db.add(article)
    await db.commit()
    return {"success": True, "data": {"id": str(article.id), "status": article.status}}


@router.post("/chat/knowledge/{article_id}/approve")
async def approve_knowledge_article(
    article_id: uuid.UUID, payload: KnowledgeArticleApprove, db: AsyncSession = Depends(get_db)
):
    article = await db.get(KnowledgeArticle, article_id)
    if article is None:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": "Article not found"}}

    article.approval_status = "approved" if payload.approve else "rejected"
    chunk_count = 0
    ingestion_error: str | None = None

    if payload.approve:
        article.status = "active"
        # Approval makes the article eligible for RAG once ingested. If the
        # embedding backend isn't configured yet, the article still gets
        # approved -- ingestion can be retried later via /ingest -- rather
        # than failing the whole approval.
        try:
            ingestion = KnowledgeIngestionService(db, get_embedding_provider())
            chunk_count = await ingestion.ingest_article(article)
        except ValueError as exc:
            ingestion_error = str(exc)

    await db.commit()
    return {
        "success": True,
        "data": {
            "id": str(article.id),
            "approval_status": article.approval_status,
            "chunks_created": chunk_count,
            "ingestion_error": ingestion_error,
        },
    }


@router.post("/chat/knowledge/{article_id}/ingest")
async def reingest_knowledge_article(article_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Manually re-chunk + re-embed an article -- use after editing content
    on an already-approved article, or after changing the embedding model."""
    try:
        embedding_provider = get_embedding_provider()
    except ValueError as exc:
        return {"success": False, "error": {"code": "EMBEDDINGS_NOT_CONFIGURED", "message": str(exc)}}

    ingestion = KnowledgeIngestionService(db, embedding_provider)
    try:
        chunk_count = await ingestion.ingest_article_by_id(article_id)
    except ValueError as exc:
        return {"success": False, "error": {"code": "NOT_FOUND", "message": str(exc)}}
    await db.commit()
    return {"success": True, "data": {"id": str(article_id), "chunks_created": chunk_count}}


@router.post("/chat/knowledge/reingest-all")
async def reingest_all_knowledge(db: AsyncSession = Depends(get_db)):
    """Bulk re-embed every active/approved article. Use this after switching
    EMBEDDING_MODEL to a model with a different output dimension (also
    requires a DB migration to resize the KnowledgeChunk.embedding column)."""
    try:
        embedding_provider = get_embedding_provider()
    except ValueError as exc:
        return {"success": False, "error": {"code": "EMBEDDINGS_NOT_CONFIGURED", "message": str(exc)}}

    ingestion = KnowledgeIngestionService(db, embedding_provider)
    counts = await ingestion.reingest_all_active()
    await db.commit()
    return {"success": True, "data": {"articles_reingested": len(counts), "chunk_counts": counts}}


@router.get("/chat/prompts")
async def list_prompts():
    from app.ai.prompts.registry import _REGISTRY

    return {
        "success": True,
        "data": [
            {"prompt_id": p.prompt_id, "version": p.version, "status": p.status}
            for p in _REGISTRY.values()
        ],
    }