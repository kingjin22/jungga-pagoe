-- ============================================================
-- 정가파괴 Admin Schema Migration
-- Supabase SQL Editor에서 실행하세요
-- ============================================================

-- deals 테이블 컬럼 추가
ALTER TABLE deals ADD COLUMN IF NOT EXISTS pinned BOOLEAN DEFAULT FALSE;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS admin_note TEXT;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS today_views INTEGER DEFAULT 0;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS total_views INTEGER DEFAULT 0;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS today_clicks INTEGER DEFAULT 0;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS total_clicks INTEGER DEFAULT 0;
ALTER TABLE deals ADD COLUMN IF NOT EXISTS last_scraped_at TIMESTAMPTZ DEFAULT NOW();

-- event_logs 테이블
CREATE TABLE IF NOT EXISTS event_logs (
  id BIGSERIAL PRIMARY KEY,
  event_type VARCHAR(50) NOT NULL,
  deal_id INTEGER REFERENCES deals(id) ON DELETE CASCADE,
  session_id VARCHAR(100),
  referrer TEXT,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_logs_deal_id ON event_logs(deal_id);
CREATE INDEX IF NOT EXISTS idx_event_logs_created_at ON event_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_event_logs_event_type ON event_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_event_logs_today ON event_logs(created_at, event_type);

-- RLS
ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "service role full access" ON event_logs FOR ALL USING (true);
