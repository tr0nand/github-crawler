CREATE TABLE IF NOT EXISTS crawl_runs (
    id SERIAL PRIMARY KEY,
    completed_at TIMESTAMPTZ DEFAULT NOW(),
    coverage_report JSONB,
    total_repos INT
);