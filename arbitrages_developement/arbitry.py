# main.py

import asyncio
from fetch_info import main as fetch_main
from compute_gains import main as compute_main

async def main():
    # Fetch information first
    prices = await fetch_main()

    # Compute gains with the fetched information
    await compute_main(prices)

if __name__ == "__main__":
    asyncio.run(main())