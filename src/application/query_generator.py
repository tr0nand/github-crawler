from dataclasses import dataclass, replace, field
from typing import Dict, List, Optional, Tuple, FrozenSet
import random

from ..domain.entities import SearchDimension
from ..domain.value_objects import QueryStrategy, CoverageStats


class QueryBuilder:
    """
    Handles the construction of GitHub search queries.
    
    Think of this as a recipe book that knows:
    - What ingredients (dimensions) are available
    - How to combine them into a query
    - How to track which combinations have been used
    """
    
    @staticmethod
    def get_dimensions() -> Tuple[SearchDimension, ...]:
        """
        Define all the ways we can search GitHub repositories.
        
        Example: To find Python repos with 100+ stars created in 2024:
        - base: "is:public" (always included)
        - language: "language:python"
        - stars: "stars:101..500"
        - created: "created:2024-01-01..2024-03-31"
        
        Returns a tuple of SearchDimension objects, each containing:
        - name: The dimension name (e.g., "language")
        - values: All possible values for that dimension
        - is_primary: Whether this dimension is always included
        """
        return (
            # Base dimension - always included in every query
            SearchDimension("base", ("is:public",), is_primary=True),
            
            # # Programming languages to search
            # SearchDimension("language", (
            #     "language:python", "language:javascript", "language:java",
            #     "language:go", "language:typescript", "language:c",
            #     "language:cpp", "language:ruby", "language:php",
            #     "language:swift", "language:rust", "language:kotlin",
            #     "language:shell", "language:r", "language:dart"
            # )),
            
            # Star count ranges - bucketed to avoid overlaps
            SearchDimension("stars", (
                "stars:0..10",      # Low popularity
                "stars:11..50",     # Growing projects
                "stars:51..100",    # Notable projects
                "stars:101..500",   # Popular projects
                "stars:501..1000",  # Very popular
                "stars:1001..5000", # Highly popular
                "stars:>5000"       # Extremely popular
            )),
            
            # Creation date ranges
            SearchDimension("created", (
                # "created:2024-01-01..2024-03-31",  # Q1 2024
                # "created:2024-04-01..2024-06-30",  # Q2 2024
                # "created:2024-07-01..2024-09-30",  # Q3 2024
                # "created:2024-10-01..2024-12-31",  # Q4 2024
                # "created:2023-01-01..2023-12-31",  # All of 2023
                # "created:<2023-01-01"              # Before 2023
                "created:2011-01-01..2011-03-31",  # Q1 2011
                "created:2011-04-01..2011-06-31",  # Q2 2011
                "created:2011-07-01..2011-09-31",  # Q3 2011
                "created:2011-10-01..2011-23-31",  # Q4 2011
                "created:2012-01-01..2012-03-31",  # Q1 2012
                "created:2012-04-01..2012-06-31",  # Q2 2012
                "created:2012-07-01..2012-09-31",  # Q3 2012
                "created:2012-10-01..2012-23-31",  # Q4 2012
                "created:2013-01-01..2013-03-31",  # Q1 2013
                "created:2013-04-01..2013-06-31",  # Q2 2013
                "created:2013-07-01..2013-09-31",  # Q3 2013
                "created:2013-10-01..2013-23-31",  # Q4 2013
            )),
            
            # Repository size (in KB)
            SearchDimension("size", (
                "size:1..100",      # Tiny repos
                "size:101..1000",   # Small repos
                "size:1001..10000", # Medium repos
                "size:>10000"       # Large repos
            )),
            
            # Activity indicators
            SearchDimension("activity", (
                "forks:>5",         # Highly forked
                "forks:1..5",       # Some forks
                "forks:0",          # No forks
                "issues:>10",       # Many issues
                "issues:1..10",     # Some issues
                "archived:false",   # Active repos
                "archived:true"     # Archived repos
            ))
        )
    
    @staticmethod
    def build_query(dimensions_used: Dict[str, str]) -> str:
        """
        Combine dimension values into a GitHub search query.
        
        Example:
            Input: {"base": "is:public", "language": "language:python", "stars": "stars:>100"}
            Output: "is:public language:python stars:>100"
        """
        return " ".join(dimensions_used.values())
    
    @staticmethod
    def calculate_dimension_coverage(coverage: CoverageStats, dimensions: Tuple[SearchDimension, ...]) -> Dict[str, float]:
        """
        Calculate what percentage of each dimension we've explored.
        
        Example:
            If we have 15 languages and we've used 10 of them in queries,
            the coverage for "language" would be 10/15 = 0.667 (66.7%)
        
        This helps us identify which dimensions need more exploration.
        """
        result = {}
        for dim in dimensions:
            if dim.is_primary:  # Skip base dimensions
                continue
            
            # Get the usage statistics for this dimension
            stats = coverage.dimension_stats.get(dim.name, {})
            
            # Count how many times we've used any value from this dimension
            total_uses = sum(stats.values())
            
            # Calculate coverage as a ratio (0.0 to 1.0)
            coverage_ratio = total_uses / len(dim.values) if dim.values else 0
            result[dim.name] = coverage_ratio
            
        return result
    
    @staticmethod
    def find_least_used_value(coverage: CoverageStats, dimension: str, values: Tuple[str, ...]) -> str:
        """
        Find which value in a dimension has been used the least.
        
        Example:
            If "language:python" has been used 100 times but "language:dart" 
            only 5 times, this will return "language:dart"
        
        This ensures we explore underrepresented areas of GitHub.
        """
        stats = coverage.dimension_stats.get(dimension, {})
        # Return the value with minimum usage count (default 0 for unused)
        return min(values, key=lambda v: stats.get(v, 0))


def _create_initial_coverage_stats(dimensions: Tuple[SearchDimension, ...]) -> CoverageStats:
    """
    Create a fresh coverage tracker with all counters at zero.
    
    Like a new scoreboard where no games have been played yet.
    """
    stats_dict = {}
    for dim in dimensions:
        # Initialize each dimension value with a count of 0
        stats_dict[dim.name] = {val: 0 for val in dim.values}
    return CoverageStats(stats_dict)


@dataclass(frozen=True)
class QueryGeneratorState:
    """
    The immutable state of our query generator.
    
    Think of this as a snapshot in time that contains:
    - All possible search dimensions
    - Which query combinations we've already tried
    - How many times we've used each dimension value
    
    Being immutable means we create a new state for each change,
    allowing us to track history and avoid side effects.
    """
    # All available search dimensions
    dimensions: Tuple[SearchDimension, ...] = field(default_factory=QueryBuilder.get_dimensions)
    
    # Set of all query combinations we've already used
    # Each combination is a frozen set of (dimension, value) pairs
    used_combinations: FrozenSet[FrozenSet[Tuple[str, str]]] = field(default_factory=frozenset)
    
    # Tracks how many repos we've found for each dimension value
    coverage_stats: CoverageStats = field(default=None)
    
    def __post_init__(self):
        """Initialize coverage stats if not provided"""
        if self.coverage_stats is None:
            # Create fresh coverage stats with all counters at 0
            object.__setattr__(self, 'coverage_stats', _create_initial_coverage_stats(self.dimensions))
    
    def with_used_combination(self, combo: FrozenSet[Tuple[str, str]]) -> 'QueryGeneratorState':
        """
        Create a new state that includes this query combination as "used".
        
        Example:
            If combo = {("language", "python"), ("stars", ">100")}
            This marks that combination as already tried.
        """
        return replace(
            self,
            used_combinations=self.used_combinations | {combo}
        )
    
    def with_updated_coverage(self, dimension: str, value: str, count: int) -> 'QueryGeneratorState':
        """
        Create a new state with updated coverage statistics.
        
        Example:
            If we found 150 repos for "language:python", we'd call:
            with_updated_coverage("language", "language:python", 150)
        """
        return replace(
            self,
            coverage_stats=self.coverage_stats.update(dimension, value, count)
        )


class QueryGenerator:
    """
    Generates GitHub search queries intelligently to maximize coverage.
    
    How it works:
    1. Tracks which combinations have been tried
    2. Prioritizes underexplored dimensions
    3. Combines multiple dimensions for specific searches
    4. Returns a new generator instance with updated state (immutable)
    
    Example usage:
        generator = QueryGenerator()
        queries, new_generator = generator.generate_batch(5)
        # 'generator' is unchanged, 'new_generator' has updated state
    """
    
    def __init__(self, state: Optional[QueryGeneratorState] = None):
        """Initialize with given state or create a fresh one"""
        self.state = state or QueryGeneratorState()
    
    def generate_batch(self, batch_size: int) -> Tuple[List[QueryStrategy], 'QueryGenerator']:
        """
        Generate multiple queries at once for concurrent execution.
        
        Args:
            batch_size: How many queries to generate (e.g., 15)
            
        Returns:
            - List of QueryStrategy objects to execute
            - New QueryGenerator with updated state
            
        Example:
            queries, new_gen = generator.generate_batch(15)
            # queries = [QueryStrategy(...), QueryStrategy(...), ...]
            # new_gen = QueryGenerator with all 15 queries marked as used
        """
        queries = []
        current_state = self.state
        
        for _ in range(batch_size):
            query, current_state = self._generate_single_query(current_state)
            if query:
                queries.append(query)
            else:
                # No more unique combinations available
                break
        
        # Return queries and new generator with updated state
        return queries, QueryGenerator(current_state)
    
    def _generate_single_query(self, state: QueryGeneratorState) -> Tuple[Optional[QueryStrategy], QueryGeneratorState]:
        """
        Generate one query using our smart targeting algorithm.
        
        Strategy:
        1. Find which dimensions have lowest coverage
        2. Try to create a query targeting those dimensions
        3. If that fails, fall back to random combinations
        """
        # Calculate coverage percentage for each dimension
        coverage = QueryBuilder.calculate_dimension_coverage(state.coverage_stats, state.dimensions)
        
        # Sort dimensions by coverage (lowest first)
        # Example: [("activity", 0.1), ("size", 0.2), ("created", 0.3), ...]
        sorted_dims = sorted(coverage.items(), key=lambda x: x[1])
        
        # Try targeted approach first (focus on least covered dimensions)
        for target_dim_name, coverage_percent in sorted_dims:
            query, new_state = self._create_targeted_query(state, target_dim_name)
            if query:
                return query, new_state
        
        # If targeted approach fails, try random combinations
        return self._create_random_query(state)
    
    def _create_targeted_query(self, state: QueryGeneratorState, target_dim_name: str) -> Tuple[Optional[QueryStrategy], QueryGeneratorState]:
        """
        Create a query specifically targeting an underexplored dimension.
        
        Example:
            If "activity" dimension has low coverage, this might generate:
            "is:public language:dart archived:true stars:>5000"
            where "archived:true" is from the targeted "activity" dimension
        """
        # Find the dimension object
        target_dim = next((d for d in state.dimensions if d.name == target_dim_name), None)
        if not target_dim:
            return None, state
        
        # Start building our query
        dimensions_used = {}
        
        # Step 1: Add required dimensions (like "is:public")
        for dim in state.dimensions:
            if dim.is_primary:
                dimensions_used[dim.name] = dim.values[0]
        
        # Step 2: Add least used value from our target dimension
        least_used_value = QueryBuilder.find_least_used_value(
            state.coverage_stats, 
            target_dim_name, 
            target_dim.values
        )
        dimensions_used[target_dim_name] = least_used_value
        
        # Step 3: Add 1-2 complementary dimensions (also picking least used values)
        other_dims = [d for d in state.dimensions 
                     if not d.is_primary and d.name != target_dim_name]
        
        for other_dim in other_dims[:2]:  # Take at most 2 additional dimensions
            least_used = QueryBuilder.find_least_used_value(
                state.coverage_stats, 
                other_dim.name, 
                other_dim.values
            )
            dimensions_used[other_dim.name] = least_used
        
        # Step 4: Check if we've already tried this combination
        combo_key = frozenset(dimensions_used.items())
        if combo_key in state.used_combinations:
            return None, state  # Already tried this combination
        
        # Step 5: Create the query
        query = QueryStrategy(
            query=QueryBuilder.build_query(dimensions_used),
            dimensions=dimensions_used,
            priority=10 - len(dimensions_used)  # Fewer dimensions = higher priority
        )
        
        # Return query and new state with this combination marked as used
        return query, state.with_used_combination(combo_key)
    
    def _create_random_query(self, state: QueryGeneratorState) -> Tuple[Optional[QueryStrategy], QueryGeneratorState]:
        """
        Create a random query combination as a fallback strategy.
        
        This is used when targeted generation can't find new combinations.
        We try up to 50 random combinations to find an unused one.
        """
        max_attempts = 50
        
        for attempt in range(max_attempts):
            dimensions_used = {}
            
            # Add required dimensions
            for dim in state.dimensions:
                if dim.is_primary:
                    dimensions_used[dim.name] = dim.values[0]
            
            # Randomly select 2-3 other dimensions
            other_dims = [d for d in state.dimensions if not d.is_primary]
            num_dims_to_select = min(3, len(other_dims))
            selected_dims = random.sample(other_dims, num_dims_to_select)
            
            # For each selected dimension, pick a random value
            for dim in selected_dims:
                random_value = random.choice(dim.values)
                dimensions_used[dim.name] = random_value
            
            # Check if this combination is new
            combo_key = frozenset(dimensions_used.items())
            if combo_key not in state.used_combinations:
                # Found a new combination!
                query = QueryStrategy(
                    query=QueryBuilder.build_query(dimensions_used),
                    dimensions=dimensions_used,
                    priority=5  # Medium priority for random queries
                )
                return query, state.with_used_combination(combo_key)
        
        # Couldn't find any new combinations
        return None, state
    
    def update_coverage(self, strategy: QueryStrategy, repos_found: int) -> 'QueryGenerator':
        """
        Update coverage statistics after executing a query.
        
        Example:
            If a query with "language:python" and "stars:>100" found 250 repos,
            both dimension values get credited with finding 250 repos.
        
        Returns a new QueryGenerator with updated statistics.
        """
        new_state = self.state
        
        # Update count for each dimension value used in the query
        for dim_name, value in strategy.dimensions.items():
            new_state = new_state.with_updated_coverage(dim_name, value, repos_found)
        
        return QueryGenerator(new_state)
    
    def get_coverage_report(self) -> Dict:
        """
        Generate a detailed report of our search coverage.
        
        Example output:
        {
            "total_queries": 1500,
            "dimension_coverage": {
                "language": {
                    "values_covered": 14,
                    "total_values": 15,
                    "coverage_percentage": 93.3,
                    "repos_per_value": {
                        "language:python": 15234,
                        "language:javascript": 14567,
                        ...
                    }
                },
                ...
            }
        }
        """
        report = {
            "total_queries": len(self.state.used_combinations),
            "dimension_coverage": {}
        }
        
        for dim in self.state.dimensions:
            if dim.is_primary:
                continue  # Skip base dimensions in report
            
            # Get coverage data for this dimension
            coverage_data = self.state.coverage_stats.dimension_stats.get(dim.name, {})
            
            # Count how many values have been used at least once
            values_with_coverage = sum(1 for count in coverage_data.values() if count > 0)
            
            # Calculate coverage percentage
            coverage_pct = (values_with_coverage / len(dim.values) * 100) if dim.values else 0
            
            # Build dimension report
            report["dimension_coverage"][dim.name] = {
                "values_covered": values_with_coverage,
                "total_values": len(dim.values),
                "coverage_percentage": coverage_pct,
                "repos_per_value": {k: v for k, v in coverage_data.items() if v > 0}
            }
        
        return report
