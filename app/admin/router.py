import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_roles
from app.common.enums.chat import UserRole
from app.database.session import get_db
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
    if payload.approve:
        article.status = "active"
    await db.commit()
    return {"success": True, "data": {"id": str(article.id), "approval_status": article.approval_status}}


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
