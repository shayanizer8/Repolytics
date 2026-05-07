import asyncio
from core.fetcher import get_repo


async def main():
    data = await get_repo("https://github.com/tiangolo/fastapi")
    print("Name:", data["name"])
    print("Stars:", data["stars"])
    print("Languages:", data["languages"])
    print("Files:", data["file_tree"][:5])
    print("README preview:", data["readme"][:200])


asyncio.run(main())
