-- 커뮤니티 딜 원글 URL 저장 (만료 감지에 사용)
ALTER TABLE deals ADD COLUMN IF NOT EXISTS source_post_url TEXT;
CREATE INDEX IF NOT EXISTS idx_deals_source_post ON deals(source_post_url) WHERE source_post_url IS NOT NULL;
