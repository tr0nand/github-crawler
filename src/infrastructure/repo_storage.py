from typing import List, Dict, Union
import asyncpg
import json

from ..domain.entities import Repository

class RepoStorage:
    """Database storage for repositories"""
    
    def __init__(self, db: Union[asyncpg.Connection, asyncpg.Pool]):
        self.db = db
    
    async def save_repositories(self, repos: List[Repository]) -> None:
        """Save repositories to database"""
        if not repos:
            return
        
        values = [(r.id, r.full_name, r.stars) for r in repos]
        
        # Handle both connection and pool
        if isinstance(self.db, asyncpg.Pool):
            async with self.db.acquire() as conn:
                await conn.executemany(
                    """INSERT INTO repositories(id, full_name, stars)
                       VALUES($1, $2, $3)
                       ON CONFLICT(id) DO UPDATE
                       SET stars = EXCLUDED.stars,
                           scraped_at = NOW()""",
                    values
                )
        else:
            await self.db.executemany(
                """INSERT INTO repositories(id, full_name, stars)
                   VALUES($1, $2, $3)
                   ON CONFLICT(id) DO UPDATE
                   SET stars = EXCLUDED.stars,
                       scraped_at = NOW()""",
                values
            )
    
    async def count_repositories(self) -> int:
        """Get total repository count"""
        if isinstance(self.db, asyncpg.Pool):
            async with self.db.acquire() as conn:
                return await conn.fetchval("SELECT COUNT(*) FROM repositories")
        else:
            return await self.db.fetchval("SELECT COUNT(*) FROM repositories")
    
    async def save_coverage_report(self, report: Dict, total_repos: int) -> None:
        """Save coverage report"""
        if isinstance(self.db, asyncpg.Pool):
            async with self.db.acquire() as conn:
                await conn.execute(
                    """INSERT INTO crawl_runs(completed_at, coverage_report, total_repos)
                       VALUES(NOW(), $1, $2)""",
                    json.dumps(report),
                    total_repos
                )
        else:
            await self.db.execute(
                """INSERT INTO crawl_runs(completed_at, coverage_report, total_repos)
                   VALUES(NOW(), $1, $2)""",
                json.dumps(report),
                total_repos
            )