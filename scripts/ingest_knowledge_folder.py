"""
Bulk-load knowledge base articles from local files.

Usage:
    python -m scripts.ingest_knowledge_folder ./knowledge_content --category cancellation --language en --approve

Expected folder layout: one file per article. The first line of the file is
used as the title, the rest is the content, e.g.:

    Cancellation fee policy
    Riders are charged a cancellation fee if they cancel more than 2 minutes
    after a driver accepts...

Each file becomes one KnowledgeArticle. Pass --approve to immediately mark
articles approved+active and run ingestion (chunk + embed); otherwise they
land as drafts pending review via the admin API.
"""
import argparse
import asyncio
from pathlib import Path

from app.database.session import AsyncSessionLocal
from app.knowledge.embeddings.provider import get_embedding_provider
from app.knowledge.ingestion.service import KnowledgeIngestionService
from app.knowledge.models import KnowledgeArticle


async def ingest_folder(folder: Path, *, category: str, language: str, approve: bool) -> None:
    files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix in (".md", ".txt")])
    if not files:
        print(f"No .md/.txt files found in {folder}")
        return

    async with AsyncSessionLocal() as db:
        ingestion = KnowledgeIngestionService(db, get_embedding_provider()) if approve else None

        for file_path in files:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            title = lines[0].strip() if lines else file_path.stem
            content = "\n".join(lines[1:]).strip() or file_path.read_text(encoding="utf-8")

            article = KnowledgeArticle(
                title=title,
                content=content,
                category=category,
                language=language,
                status="active" if approve else "draft",
                approval_status="approved" if approve else "pending",
            )
            db.add(article)
            await db.flush()

            chunk_count = 0
            if approve and ingestion:
                chunk_count = await ingestion.ingest_article(article)

            print(f"[{'ingested' if approve else 'draft'}] {title} ({chunk_count} chunks) -> {article.id}")

        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-load knowledge articles from a folder")
    parser.add_argument("folder", type=Path, help="Folder containing .md/.txt article files")
    parser.add_argument("--category", required=True, help="Knowledge category, e.g. cancellation, refund, fare")
    parser.add_argument("--language", default="en", help="Article language code (en, hi, hi-en)")
    parser.add_argument("--approve", action="store_true", help="Approve + embed immediately instead of leaving as draft")
    args = parser.parse_args()

    asyncio.run(ingest_folder(args.folder, category=args.category, language=args.language, approve=args.approve))


if __name__ == "__main__":
    main()