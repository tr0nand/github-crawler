"""Entry point for GitHub Actions"""
import asyncio
from src.main import run_crawler

if __name__ == "__main__":
    asyncio.run(run_crawler())