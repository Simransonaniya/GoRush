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


@router.get("/chat/conversations")
async def list_conversations(
    language: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    from app.chat.models import ChatSession

    stmt = select(ChatSession)
    if language:
        stmt = stmt.where(ChatSession.language == language)
    if status:
        stmt = stmt.where(ChatSession.status == status)

    stmt = stmt.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    sessions = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "session_id": str(s.id),
                "user_id": str(s.user_id),
                "language": s.language,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
            }
            for s in sessions
        ],
        "meta": {"limit": limit, "offset": offset},
    }


@router.get("/chat/agent-queue")
async def list_agent_queue(
    priority: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from app.handoff.models import Handoff

    stmt = select(Handoff).order_by(Handoff.created_at.desc())
    if priority:
        stmt = stmt.where(Handoff.priority == priority)

    result = await db.execute(stmt)
    handoffs = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "handoff_id": str(h.id),
                "session_id": str(h.session_id),
                "user_id": str(h.user_id),
                "priority": h.priority,
                "reason": h.reason,
                "summary": h.summary,
                "context_snapshot": h.context_snapshot,
                "resolved": h.resolved,
                "created_at": h.created_at.isoformat(),
            }
            for h in handoffs
        ],
    }


@router.post("/chat/conversations/{session_id}/takeover")
async def takeover_conversation(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    from app.chat.models import ChatSession
    from app.common.enums.chat import SessionStatus
    from app.common.exceptions.base import NotFoundError

    session = await db.get(ChatSession, session_id)
    if session is None:
        raise NotFoundError("Session not found")

    session.status = SessionStatus.HANDED_OFF.value
    await db.commit()

    return {
        "success": True,
        "data": {
            "session_id": str(session.id),
            "status": session.status,
            "message": "Human agent takeover successful.",
        },
    }


@router.get("/chat/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func

    from app.chat.models import ChatMessage, ChatSession, Feedback
    from app.handoff.models import Handoff
    from app.tools.models import ToolCall

    res_sessions = await db.execute(select(func.count(ChatSession.id)))
    total_sessions = res_sessions.scalar() or 0

    res_messages = await db.execute(select(func.count(ChatMessage.id)))
    total_messages = res_messages.scalar() or 0

    res_handoffs = await db.execute(select(func.count(Handoff.id)))
    total_handoffs = res_handoffs.scalar() or 0

    res_csat = await db.execute(select(func.avg(Feedback.rating)))
    csat_avg = round(float(res_csat.scalar() or 0.0), 2)

    res_tools = await db.execute(select(func.count(ToolCall.id)))
    total_tools = res_tools.scalar() or 0

    handoff_rate = round((total_handoffs / total_sessions * 100), 2) if total_sessions > 0 else 0.0
    containment_rate = round(100.0 - handoff_rate, 2)

    return {
        "success": True,
        "data": {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "containment_rate_pct": containment_rate,
            "handoff_rate_pct": handoff_rate,
            "total_handoffs": total_handoffs,
            "csat_average": csat_avg,
            "total_tool_calls": total_tools,
            "estimated_p50_latency_ms": 250,
            "estimated_cost_usd": round(total_messages * 0.0005, 4),
        },
    }


@router.get("/chat/audit-logs")
async def list_audit_logs(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    from app.audit.models import AuditLog

    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    )
    entries = result.scalars().all()

    return {
        "success": True,
        "data": [
            {
                "id": str(e.id),
                "request_id": e.request_id,
                "action": e.action,
                "decision": e.decision,
                "user_id": str(e.user_id) if e.user_id else None,
                "session_id": str(e.session_id) if e.session_id else None,
                "tool_name": e.tool_name,
                "details": e.details,
                "created_at": e.created_at.isoformat(),
            }
            for e in entries
        ],
        "meta": {"limit": limit, "offset": offset},
    }