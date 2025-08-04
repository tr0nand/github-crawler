import asyncio, os, asyncpg

TRUNCATE_SQL = """
TRUNCATE TABLE repositories
RESTART IDENTITY      -- zero‑out any SERIAL / IDENTITY columns
CASCADE;              -- if other tables FK‑reference this one, clear them too
"""

async def reset():
    conn = await asyncpg.connect(os.getenv("DATABASE_URL"))
    await conn.execute(TRUNCATE_SQL)
    print("✅  repositories table emptied.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(reset())
