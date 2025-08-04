# GitHub Repository Crawler

A high-performance, concurrent GitHub repository crawler that efficiently collects repository metadata using GitHub's GraphQL API. Built with clean architecture principles and designed to scale.

## 🚀 Features

- **Concurrent crawling** with configurable parallelism (15 concurrent queries by default)
- **Smart query generation** using multi-dimensional search strategies
- **Rate limit handling** with automatic pausing and retry mechanisms
- **Clean architecture** with separated domain, application, and infrastructure layers
- **Immutable data structures** throughout the codebase
- **Anti-corruption layer** for GitHub API translation
- **Coverage tracking** to ensure comprehensive data collection
- **PostgreSQL storage** with efficient upsert operations

## 📊 Performance

- Collects 100,000 repositories in under 8 minutes
- Handles GitHub API rate limits gracefully
- Minimizes duplicate API calls through intelligent query generation
- Processes ~200 repositories per second

## 🏗️ Architecture

The project follows clean architecture principles with three main layers:

### Domain Layer
- **Entities**: `Repository`, `SearchDimension`
- **Value Objects**: `QueryStrategy`, `CoverageStats`, `CrawlerStats`
- Pure data models with immutable dataclasses

### Application Layer
- **QueryGenerator**: Generates non-overlapping search queries
- **CrawlerService**: Orchestrates individual query execution
- **CrawlerOrchestrator**: Manages the overall crawling process

### Infrastructure Layer
- **GitHubClient**: Handles GitHub GraphQL API communication
- **RepoStorage**: Manages PostgreSQL database operations
- **Anti-corruption Layer**: Translates between GitHub API and domain models

## 📦 Data Schema

### Current Schema
```sql
repositories (
    id          BIGINT       PRIMARY KEY,    -- GitHub's databaseId
    full_name   TEXT         UNIQUE,         -- owner/repo format
    stars       INT,                         -- Current star count
    scraped_at  TIMESTAMPTZ  DEFAULT NOW(),  -- Last update time
    extra       JSONB        DEFAULT '{}'    -- Flexible metadata storage
)

crawl_runs (
    id              SERIAL PRIMARY KEY,
    completed_at    TIMESTAMPTZ DEFAULT NOW(),
    coverage_report JSONB,
    total_repos     INT
)
```

### Schema Evolution Strategy

The schema is designed to evolve efficiently as new metadata requirements emerge:

1. **Normalized Approach** (Recommended for structured data):
   ```sql
   -- Separate tables for each entity type
   repositories (id, full_name, stars, extra)
   pull_requests (id, repo_id, number, title, state)
   pr_comments (id, pr_id, body, created_at, author)
   issues (id, repo_id, number, title, state)
   ```

2. **Event-Driven Approach** (For audit trails and flexibility):
   ```sql
   -- Core data with immutable event history
   repositories (id, full_name, current_stars)
   repository_events (
       id, repo_id, event_type, event_data JSONB, 
       occurred_at, processed_at
   )
   ```

## 🔍 Query Generation Strategy

The crawler uses a sophisticated multi-dimensional query generation system:

### Search Dimensions
- **Language**: Python, JavaScript, Java, Go, TypeScript, etc.
- **Stars**: Bucketed ranges (0-10, 11-50, 51-100, etc.)
- **Creation Date**: Quarterly and yearly ranges
- **Repository Size**: Small to large codebases
- **Activity Metrics**: Forks, issues, archived status

### Coverage Optimization
- Tracks which dimension combinations have been queried
- Prioritizes under-explored areas of the search space
- Prevents duplicate queries through combination tracking
- Provides detailed coverage reports

See [query_builder.md](query_builder.md) for a detailed explanation with examples.

## 🚦 Getting Started

### Prerequisites
- Python 3.12+
- PostgreSQL 16+
- GitHub Personal Access Token

### Installation
```bash
# Clone the repository
git clone https://github.com/yourusername/github-crawler-stars.git
cd github-crawler-stars

# Install dependencies
pip install poetry
poetry install

# Set up environment variables
export GITHUB_TOKEN="your-github-token"
export DATABASE_URL="postgresql://user:pass@localhost:5432/dbname"
```

### Database Setup
```bash
# Create the database schema
psql -d your_database -f schema.sql
psql -d your_database -f crawl_runs.sql
```

### Running the Crawler
```bash
# Run the crawler
poetry run python crawl.py
```

## 🔄 GitHub Actions Workflow

The project includes a complete CI/CD pipeline that:
1. Sets up a PostgreSQL service container
2. Initializes the database schema
3. Runs the crawler with automatic error handling
4. Exports results as CSV artifacts

## 🚀 Future Enhancements

### Scaling to 500M+ Repositories

1. **Enhanced Query Generation**
   - Query result analysis for coverage optimization
   - Machine learning for query effectiveness prediction
   - Dynamic query adjustment based on result density

2. **Distributed Architecture**
   - Multiple worker nodes with centralized queue
   - Sharding by repository creation date
   - Delta crawling for update detection

3. **Infrastructure Improvements**
   - Caching layer for popular repositories
   - Columnar storage for analytics
   - Data lake integration for raw data archival

4. **Advanced Features**
   - Real-time update streaming
   - Change detection and notification system
   - API for querying collected data
   - Data quality monitoring and alerting

### Monitoring & Observability
- Metrics dashboard for crawl performance
- API token health monitoring
- Data distribution analysis
- Automated data quality checks

## 📈 Metrics & Monitoring

The crawler tracks:
- Total API calls and success rates
- Rate limit utilization
- Query effectiveness (repos found per query)
- Dimension coverage percentages
- Crawl duration and throughput

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## 📄 License

This project is open source and available under the [MIT License](LICENSE).