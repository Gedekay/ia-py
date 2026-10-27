import argparse
import asyncio

from sqlalchemy import select

from app.db.session import async_session_maker
from app.models.user import Role, User
from app.services.audit import log_action
from app.core.security import hash_password


async def create_admin(email: str, password: str, full_name: str) -> None:
    async with async_session_maker() as db:
        existing = await db.scalar(select(User).where(User.email == email))
        if existing is not None:
            raise SystemExit("Un compte existe déjà pour cette adresse.")
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=Role.ADMIN,
        )
        db.add(user)
        await db.flush()
        await log_action(db, user, "ADMIN_BOOTSTRAPPED", "user", user.id)
        await db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Créer le premier compte administrateur SAAJD.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--full-name", required=True)
    parser.add_argument("--password-env", default="SAAJD_ADMIN_PASSWORD")
    args = parser.parse_args()
    import os

    password = os.environ.get(args.password_env)
    if not password or len(password) < 12:
        raise SystemExit(f"Définissez {args.password_env} avec au moins 12 caractères.")
    asyncio.run(create_admin(args.email, password, args.full_name))


if __name__ == "__main__":
    main()