# Query Generation Strategy

The GitHub crawler uses an intelligent multi-dimensional query generation system to efficiently explore the entire repository space while minimizing duplicate API calls. This document explains the logic with a concrete example.

## Core Concepts

### 1. Search Dimensions

The crawler defines multiple orthogonal search dimensions:

```python
dimensions = (
    SearchDimension("base", ("is:public",), is_primary=True),
    SearchDimension("language", ("python", "javascript", "java", ...)),
    SearchDimension("stars", ("0..10", "11..50", "51..100", ...)),
    SearchDimension("created", ("2024-01-01..2024-03-31", ...)),
    SearchDimension("size", ("1..100", "101..1000", ...)),
    SearchDimension("activity", ("forks:>5", "issues:>10", ...))
)
```

### 2. Coverage Tracking

Each dimension value tracks how many times it has been used in queries:

```python
coverage_stats = {
    "language": {"python": 150, "javascript": 120, "java": 80, ...},
    "stars": {"0..10": 200, "11..50": 180, "51..100": 90, ...},
    ...
}
```

### 3. Combination Tracking

The system maintains a set of all previously used dimension combinations to prevent duplicates:

```python
used_combinations = {
    frozenset([("base", "is:public"), ("language", "python"), ("stars", "0..10")]),
    frozenset([("base", "is:public"), ("language", "javascript"), ("created", "2024")]),
    ...
}
```

## Query Generation Algorithm

### Step 1: Calculate Coverage

For each dimension, calculate the coverage percentage:

```python
coverage = {
    "language": 0.6,    # 60% of language values have been used
    "stars": 0.4,       # 40% of star ranges explored
    "created": 0.3,     # 30% of date ranges covered
    "size": 0.2,        # 20% of size buckets queried
    "activity": 0.1     # 10% of activity filters used
}
```

### Step 2: Targeted Query Generation

The algorithm prioritizes dimensions with lowest coverage:

1. Sort dimensions by coverage (ascending)
2. For the least-covered dimension, find its least-used value
3. Combine with least-used values from 1-2 other dimensions
4. Check if this combination has been used before
5. If unique, create the query

### Step 3: Fallback Strategy

If targeted generation fails (all combinations tried), fall back to random selection with unused combinations.

## Example: Generating a Batch of 5 Queries

Let's walk through generating a batch when the crawler has already collected 40,000 repositories:

### Initial State

```python
# Current coverage (simplified)
coverage_stats = {
    "language": {
        "python": 1200,      # heavily used
        "javascript": 1100,  # heavily used
        "rust": 50,         # under-explored
        "dart": 30,         # under-explored
    },
    "stars": {
        "0..10": 800,
        "11..50": 700,
        "1001..5000": 100,  # under-explored
        ">5000": 80,        # under-explored
    },
    "created": {
        "2024-01-01..2024-03-31": 600,
        "<2023-01-01": 150,  # under-explored
    }
}
```

### Query 1: Target Least Covered Dimension

1. **Identify target**: "activity" dimension (10% coverage)
2. **Select values**:
   - Base: "is:public" (required)
   - Activity: "archived:true" (least used in activity)
   - Language: "dart" (least used in language)
   - Stars: ">5000" (least used in stars)

**Generated Query**: `is:public language:dart stars:>5000 archived:true`

### Query 2: Continue with Low Coverage

1. **Target**: Still "activity" dimension
2. **Select values**:
   - Base: "is:public"
   - Activity: "issues:>10" (next least used)
   - Language: "rust" (second least used)
   - Created: "<2023-01-01" (least used date range)

**Generated Query**: `is:public language:rust created:<2023-01-01 issues:>10`

### Query 3: Explore Star Ranges

1. **Target**: "stars" dimension (now lowest after activity updates)
2. **Select values**:
   - Base: "is:public"
   - Stars: "1001..5000" (least used range)
   - Language: "rust" (still under-explored)
   - Size: "size:>10000" (least used size)

**Generated Query**: `is:public language:rust stars:1001..5000 size:>10000`

### Query 4: Date-Focused Query

1. **Target**: "created" dimension
2. **Select values**:
   - Base: "is:public"
   - Created: "<2023-01-01"
   - Language: "dart"
   - Activity: "forks:0" (unexplored)

**Generated Query**: `is:public language:dart created:<2023-01-01 forks:0`

### Query 5: Combination Coverage

1. **Target**: Multiple under-explored combinations
2. **Select values**:
   - Base: "is:public"
   - Size: "size:1..100" (small repos)
   - Stars: ">5000" (high stars)
   - Language: "rust"

**Generated Query**: `is:public language:rust stars:>5000 size:1..100`

## Results Processing

After executing the batch:

```python
# Example results
results = [
    ("Query 1", 89 repos),
    ("Query 2", 234 repos),
    ("Query 3", 156 repos),
    ("Query 4", 445 repos),
    ("Query 5", 78 repos)
]

# Update coverage for each dimension value used
# Query 1 updates:
coverage_stats["language"]["dart"] += 89
coverage_stats["stars"][">5000"] += 89
coverage_stats["activity"]["archived:true"] += 89
# ... and so on for each query
```

## Efficiency Features

### 1. Combination Uniqueness
- Never generates the same exact query twice
- Tracks ~10,000+ unique combinations efficiently

### 2. Adaptive Targeting
- Automatically shifts focus to under-explored areas
- Balances exploration vs exploitation

### 3. Concurrent Execution
- Generates batches of 15 queries for parallel execution
- Reduces total crawl time by 15x

### 4. Coverage Reporting
```
=== Coverage Report ===
language: 12/15 (80.0%)
  - python: 15,234 repos
  - javascript: 14,567 repos
  - rust: 1,234 repos
  - dart: 987 repos
  ...
stars: 6/7 (85.7%)
  - 0..10: 45,678 repos
  - 11..50: 23,456 repos
  ...
```

## Optimization Strategies

1. **Dimension Weighting**: Could prioritize certain dimensions based on expected repository distribution
2. **Query Effectiveness Tracking**: Monitor repos-per-query to identify high-yield combinations
3. **Dynamic Dimension Addition**: Add new search criteria based on discovered patterns
4. **Machine Learning**: Use historical data to predict optimal query combinations

This query generation strategy ensures comprehensive coverage of GitHub's repository space while maximizing efficiency and minimizing redundant API calls.