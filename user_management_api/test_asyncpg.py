import asyncio
import asyncpg

async def main():
    conn = await asyncpg.connect("postgresql://ums:umn09032026@localhost:5432/ums")
    print("Connected OK")
    await conn.close()

asyncio.run(main())
