CREATE TABLE IF NOT EXISTS repositories (
    id          BIGINT       PRIMARY KEY,
    full_name   TEXT         UNIQUE,
    stars       INT,
    scraped_at  TIMESTAMPTZ  DEFAULT NOW(),
    extra       JSONB        DEFAULT '{}'::jsonb
);
