from dataclasses import dataclass, replace
from typing import Dict

@dataclass(frozen=True)
class QueryStrategy:
    """Immutable query strategy"""
    query: str
    dimensions: Dict[str, str]
    priority: int = 0

@dataclass(frozen=True)
class CoverageStats:
    """Immutable coverage statistics"""
    dimension_stats: Dict[str, Dict[str, int]]
    
    def update(self, dimension: str, value: str, count: int) -> 'CoverageStats':
        """Return new CoverageStats with updated value"""
        new_stats = {k: v.copy() for k, v in self.dimension_stats.items()}
        if dimension in new_stats and value in new_stats[dimension]:
            new_stats[dimension][value] += count
        return CoverageStats(new_stats)

@dataclass(frozen=True)
class CrawlerStats:
    """Immutable crawler statistics"""
    total_api_calls: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    rate_limit_pauses: int = 0
    
    def increment(self, **kwargs) -> 'CrawlerStats':
        """Return new stats with incremented values"""
        updates = {k: getattr(self, k) + v for k, v in kwargs.items() if hasattr(self, k)}
        return replace(self, **updates)