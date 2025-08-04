import asyncio, os, asyncpg, json

async def dump():
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    rows = await conn.fetch("SELECT * FROM repositories ORDER BY stars DESC")
    for r in rows:
        print(dict(r))           # pretty prints each row as a dict

    print(len(rows))
    await conn.close()

asyncio.run(dump())
