import asyncio

import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.core.security import hash_password
from src.repositories.admin_repository import AdminRepository

app = typer.Typer(help="Stratix management CLI")


async def _create_admin(username: str, password: str) -> None:
    engine = create_async_engine(settings.POSTGRES_URL, pool_pre_ping=True)
    factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with factory() as session, session.begin():
        repo = AdminRepository(session)
        existing = await repo.get_by_username(username)
        if existing:
            typer.echo(f"Admin '{username}' already exists.")
            await engine.dispose()
            raise typer.Exit(1)
        password_hash = hash_password(password)
        admin = await repo.create(username, password_hash)
        typer.echo(f"Admin '{admin.username}' created (id={admin.id}).")
    await engine.dispose()


@app.command()
def createsuperuser(
    username: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    if len(password) < 6:
        typer.echo("Password must be at least 6 characters.")
        raise typer.Exit(1)
    asyncio.run(_create_admin(username, password))


if __name__ == "__main__":
    app()
