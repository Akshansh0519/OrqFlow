import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.models import Base, User
from app.auth import hash_password

async def init_test_user():
    # Use SQLite for guaranteed local testing without Docker
    db_url = "sqlite+aiosqlite:///./orqflow.db"
    engine = create_async_engine(db_url, connect_args={"check_same_thread": False})
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        # Check if user exists
        from sqlalchemy import select
        res = await session.execute(select(User).where(User.email == "test@orqflow.ai"))
        existing = res.scalar_one_or_none()
        if not existing:
            user = User(
                id=uuid.uuid4(),
                email="test@orqflow.ai",
                username="testuser",
                password_hash=hash_password("password123")
            )
            session.add(user)
            await session.commit()
            print("Successfully created test user: test@orqflow.ai / password123")
        else:
            print("Test user already exists: test@orqflow.ai / password123")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_test_user())
