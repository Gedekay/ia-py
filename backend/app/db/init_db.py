from sqlalchemy import select, text

from app.db.base import Base
from app.db.session import engine
from app.models import analyse, audit_log, constitutional_article, document, dossier, user
from app.db.session import async_session_maker
from app.models.constitutional_article import ConstitutionalArticle
from app.services.constitutional import load_articles


async def create_all() -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)


async def seed_roles() -> None:
    return None


async def seed_constitutional_articles() -> None:
    source_articles = load_articles()
    async with async_session_maker() as session:
        existing = await session.scalars(select(ConstitutionalArticle))
        by_key = {(article.numero, article.alinea): article for article in existing}
        for source in source_articles:
            article = by_key.get((source.numero, source.alinea))
            if article is None:
                session.add(
                    ConstitutionalArticle(
                        numero=source.numero,
                        alinea=source.alinea,
                        texte=source.texte,
                        theme=source.theme,
                    )
                )
            else:
                article.texte = source.texte
                article.theme = source.theme
        await session.commit()