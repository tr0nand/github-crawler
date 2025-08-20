from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    """Immutable configuration settings"""
    repos_per_page: int = 100
    target_total_repos: int = 1000000
    max_pages_per_query: int = 10
    pause_between_queries: float = 0.05
    max_concurrent_queries: int = 15
    rate_limit_threshold: int = 50
    rate_limit_wait_time: int = 60
    server_error_wait_time: int = 10
    stagnation_threshold: int = 5
    coverage_report_interval: int = 10
