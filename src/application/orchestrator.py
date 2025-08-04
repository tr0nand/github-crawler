import asyncio
from typing import Dict

from ..config import Config
from ..domain.value_objects import CrawlerStats
from ..infrastructure.repo_storage import RepoStorage
from .query_generator import QueryGenerator
from .crawler_service import CrawlerService

class CrawlerOrchestrator:
    """Orchestrates the entire crawling process"""
    
    def __init__(self, crawler_service: CrawlerService, repo_storage: RepoStorage, config: Config):
        self.crawler_service = crawler_service
        self.repo_storage = repo_storage
        self.config = config
    
    async def run(self) -> None:
        """Run the crawling process"""
        query_generator = QueryGenerator()
        stats = CrawlerStats()
        
        batch_count = 0
        last_count = 0
        stagnation_counter = 0
        
        print(f"Starting systematic crawl with concurrency")
        print(f"Target: {self.config.target_total_repos:,} unique repositories")
        print(f"Max concurrent queries: {self.config.max_concurrent_queries}")
        
        while True:
            current_count = await self.repo_storage.count_repositories()
            
            if current_count >= self.config.target_total_repos:
                print(f"TARGET REACHED! Database contains {current_count:,} unique repositories")
                break
            
            # Check stagnation
            if current_count == last_count:
                stagnation_counter += 1
                if stagnation_counter > self.config.stagnation_threshold:
                    print(f"Warning: No new unique repos in last {self.config.stagnation_threshold} batches")
            else:
                stagnation_counter = 0
            last_count = current_count
            
            # Generate queries
            queries, query_generator = query_generator.generate_batch(self.config.max_concurrent_queries)
            if not queries:
                print("No more unique query combinations available")
                break
            
            batch_count += 1
            print(f"\n--- Batch {batch_count} | Current: {current_count:,}/{self.config.target_total_repos:,} ---")
            print(f"Executing {len(queries)} queries concurrently...")
            
            try:
                batch_repos, stats = await self.crawler_service.execute_batch(queries, stats)
                print(f"Batch {batch_count} collected {batch_repos} repos")
                
                # Update coverage
                for query in queries:
                    query_generator = query_generator.update_coverage(query, batch_repos // len(queries))
                
                await asyncio.sleep(self.config.pause_between_queries)
                
            except Exception as e:
                print(f"Batch error: {e}")
                continue
            
            # Periodic coverage report
            if batch_count % self.config.coverage_report_interval == 0:
                self._print_coverage_report(query_generator.get_coverage_report())
        
        # Final report
        await self._print_final_report(query_generator, stats, batch_count)
    
    def _print_coverage_report(self, report: Dict) -> None:
        """Print coverage report"""
        print("\n=== Coverage Report ===")
        for dim, data in report["dimension_coverage"].items():
            print(f"{dim}: {data['values_covered']}/{data['total_values']} "
                  f"({data['coverage_percentage']:.1f}%)")
    
    async def _print_final_report(self, query_generator: QueryGenerator, stats: CrawlerStats, batch_count: int) -> None:
        """Print final report and save to database"""
        final_count = await self.repo_storage.count_repositories()
        final_report = query_generator.get_coverage_report()
        
        await self.repo_storage.save_coverage_report(final_report, final_count)
        
        print(f"\n{'='*50}")
        print(f"CRAWL COMPLETE!")
        print(f"{'='*50}")
        print(f"Repositories collected: {final_count:,}/{self.config.target_total_repos:,}")
        print(f"Total batches executed: {batch_count}")
        print(f"Successful queries: {stats.successful_queries}")
        print(f"Failed queries: {stats.failed_queries}")
        print(f"Total API calls: {stats.total_api_calls}")
        print(f"Rate limit pauses: {stats.rate_limit_pauses}")
        
        print(f"\n=== Final Coverage Report ===")
        for dim, data in final_report["dimension_coverage"].items():
            print(f"\n{dim.upper()}:")
            print(f"  Coverage: {data['values_covered']}/{data['total_values']} "
                  f"({data['coverage_percentage']:.1f}%)")
            if len(data['repos_per_value']) <= 10:
                for value, count in data['repos_per_value'].items():
                    print(f"  - {value}: {count:,} repos")