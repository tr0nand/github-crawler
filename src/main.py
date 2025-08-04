import asyncio
import asyncpg
import os
from gql import Client
from gql.transport.httpx import HTTPXAsyncTransport
from typing import Union

from .config import Config
from .infrastructure.github_client import GitHubClient
from .infrastructure.repo_storage import RepoStorage
from .application.crawler_service import CrawlerService
from .application.orchestrator import CrawlerOrchestrator


async def create_github_session() -> Client:
    """Create GitHub GraphQL client"""
    transport = HTTPXAsyncTransport(
        url="https://api.github.com/graphql",
        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"}
    )
    return Client(transport=transport, fetch_schema_from_transport=False)

async def run_crawler() -> None:
    """Main crawler execution"""
    db_pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"],
        min_size=1,
        max_size=20  # Enough for concurrent queries
    )
    
    async with await create_github_session() as session:
        # Wire up dependencies
        config = Config()
        github_client = GitHubClient(session)
        repo_storage = RepoStorage(db_pool)
        crawler_service = CrawlerService(github_client, repo_storage, config)
        orchestrator = CrawlerOrchestrator(crawler_service, repo_storage, config)
        
        # Run crawler
        await orchestrator.run()
    
    await db_pool.close()