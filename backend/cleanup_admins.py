import asyncio

from app.config import settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


async def main():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        # Delete all users EXCEPT admin@example.com and the demo accounts
        # The demo accounts use emails from DEMO_ACCOUNTS which we can just skip by checking roles or emails.
        # Let's just delete the ones we just created.
        emails_to_delete = [
            "sita.superadmin@sita.co.za",
            "client.superadmin@gov.za",
            "dha.admin@gov.za",
            "treasury.admin@gov.za",
            "doj.admin@gov.za",
            "health.admin@gov.za",
            "dpsa.admin@gov.za",
            "saps.admin@gov.za",
            "defence.admin@gov.za",
            "cogta.admin@gov.za",
            "doc.admin@gov.za",
            "presidency.admin@gov.za",
            "dha.branch@gov.za",
            "treasury.branch@gov.za",
            "dpsa.branch@gov.za",
        ]
        
        await session.execute(
            text("DELETE FROM identity.users WHERE email = ANY(:emails)"),
            {"emails": emails_to_delete}
        )
        await session.commit()
        print("Deleted generated admin accounts from database.")

if __name__ == "__main__":
    asyncio.run(main())
