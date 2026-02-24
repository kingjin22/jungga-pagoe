-- B-001: 딜 가격 히스토리 로그 테이블
-- _verify_prices() 스케줄러가 10분마다 가격 검증 시 로그를 기록합니다.
-- Supabase SQL Editor에서 실행하세요.

CREATE TABLE IF NOT EXISTS deal_price_log (
  id BIGSERIAL PRIMARY KEY,
  deal_id BIGINT NOT NULL REFERENCES deals(id) ON DELETE CASCADE,
  price INTEGER NOT NULL,
  source TEXT DEFAULT 'verify',
  recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deal_price_log_deal_id ON deal_price_log(deal_id, recorded_at DESC);
