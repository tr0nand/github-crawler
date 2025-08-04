import asyncio
from typing import List, Tuple

from gql.transport.exceptions import TransportQueryError, TransportServerError

from ..config import Config
from ..domain.value_objects import QueryStrategy, CrawlerStats
from ..infrastructure.github_client import GitHubClient
from ..infrastructure.repo_storage import RepoStorage
from ..infrastructure.anti_corruption.github_translator import GitHubTranslator

class CrawlerService:
    """Main crawler service orchestrating the crawl"""
    
    def __init__(self, github_client: GitHubClient, repo_storage: RepoStorage, config: Config):
        self.github_client = github_client
        self.repo_storage = repo_storage
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent_queries)
    
    async def execute_query(self, strategy: QueryStrategy, stats: CrawlerStats) -> Tuple[int, CrawlerStats]:
        """Execute a single query and return repos count and updated stats"""
        async with self.semaphore:
            return await self._execute_single_query(strategy, stats)
    
    async def _execute_single_query(self, strategy: QueryStrategy, stats: CrawlerStats) -> Tuple[int, CrawlerStats]:
        """Execute query implementation"""
        print(f"Executing: {strategy.query}")
        print(f"Dimensions: {strategy.dimensions}")
        
        cursor = None
        repos_collected = 0
        pages_processed = 0
        current_stats = stats.increment(total_api_calls=1)
        
        while pages_processed < self.config.max_pages_per_query:
            try:
                result = await self.github_client.search_repositories(strategy.query, cursor)
                
            except TransportQueryError as e:
                if GitHubTranslator.is_access_error(str(e)):
                    print(f"   WARNING: Query hit access restriction")
                    return 0, current_stats.increment(failed_queries=1)
                raise
                
            except TransportServerError:
                print(f"   PAUSE: Server error, waiting {self.config.server_error_wait_time}s...")
                await asyncio.sleep(self.config.server_error_wait_time)
                continue
            
            # Check rate limit using translated result
            if result.rate_limit.remaining < self.config.rate_limit_threshold:
                current_stats = current_stats.increment(rate_limit_pauses=1)
                print(f"   RATE LIMIT: Remaining {result.rate_limit.remaining}, waiting {self.config.rate_limit_wait_time}s")
                await asyncio.sleep(self.config.rate_limit_wait_time)
            
            # Process repositories from translated result
            if not result.repositories:
                break
            
            await self.repo_storage.save_repositories(result.repositories)
            repos_collected += len(result.repositories)
            pages_processed += 1
            print(f"   Page {pages_processed}: +{len(result.repositories)} repos")
            
            # Check for more pages
            if not result.has_next_page:
                break
            
            cursor = result.end_cursor
        
        if repos_collected > 0:
            current_stats = current_stats.increment(successful_queries=1)
        
        return repos_collected, current_stats
    
    def _is_access_error(self, error_message: str) -> bool:
        """Check if error is due to access restrictions"""
        skip_conditions = [
            "IP allow list enabled", "Must have push access", "Resource not accessible",
            "rate limit exceeded", "Forbidden", "SAML SSO", "blocked", 
            "private repository", "requires authentication"
        ]
        return any(condition.lower() in error_message.lower() for condition in skip_conditions)
    
    async def execute_batch(self, strategies: List[QueryStrategy], stats: CrawlerStats) -> Tuple[int, CrawlerStats]:
        """Execute multiple queries concurrently"""
        if not strategies:
            return 0, stats
        
        tasks = [self.execute_query(strategy, stats) for strategy in strategies]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_repos = 0
        final_stats = stats
        
        for result in results:
            if isinstance(result, tuple):
                repos, updated_stats = result
                total_repos += repos
                # Merge stats
                final_stats = final_stats.increment(
                    total_api_calls=updated_stats.total_api_calls - stats.total_api_calls,
                    successful_queries=updated_stats.successful_queries - stats.successful_queries,
                    failed_queries=updated_stats.failed_queries - stats.failed_queries,
                    rate_limit_pauses=updated_stats.rate_limit_pauses - stats.rate_limit_pauses
                )
            else:
                print(f"Query failed with error: {result}")
        
        return total_repos, final_stats