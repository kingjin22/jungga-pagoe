-- ================================================
-- 005_enable_rls.sql
-- Supabase Security Advisor 권장 사항 대응
-- RLS (Row Level Security) 활성화
-- ================================================

-- 1. deals 테이블
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;

-- 읽기: 전체 공개
CREATE POLICY "deals_public_read"
  ON deals FOR SELECT
  USING (true);

-- 쓰기: service_role (백엔드) 전용
CREATE POLICY "deals_service_write"
  ON deals FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- 2. price_snapshots 테이블
ALTER TABLE price_snapshots ENABLE ROW LEVEL SECURITY;

CREATE POLICY "price_snapshots_public_read"
  ON price_snapshots FOR SELECT
  USING (true);

CREATE POLICY "price_snapshots_service_write"
  ON price_snapshots FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- 3. brands 테이블 (있는 경우)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'brands') THEN
    ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
    
    -- 중복 정책 방지
    DROP POLICY IF EXISTS "brands_public_read" ON brands;
    DROP POLICY IF EXISTS "brands_service_write" ON brands;
    
    CREATE POLICY "brands_public_read" ON brands FOR SELECT USING (true);
    CREATE POLICY "brands_service_write" ON brands FOR ALL
      USING (auth.role() = 'service_role')
      WITH CHECK (auth.role() = 'service_role');
  END IF;
END $$;

-- 4. event_logs 테이블 (있는 경우)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'event_logs') THEN
    ALTER TABLE event_logs ENABLE ROW LEVEL SECURITY;
    
    DROP POLICY IF EXISTS "event_logs_service_all" ON event_logs;
    
    -- 이벤트 로그는 백엔드만 접근
    CREATE POLICY "event_logs_service_all" ON event_logs FOR ALL
      USING (auth.role() = 'service_role')
      WITH CHECK (auth.role() = 'service_role');
  END IF;
END $$;

-- 5. price_history 테이블 (있는 경우)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'price_history') THEN
    ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
    
    DROP POLICY IF EXISTS "price_history_public_read" ON price_history;
    DROP POLICY IF EXISTS "price_history_service_write" ON price_history;
    
    CREATE POLICY "price_history_public_read" ON price_history FOR SELECT USING (true);
    CREATE POLICY "price_history_service_write" ON price_history FOR ALL
      USING (auth.role() = 'service_role')
      WITH CHECK (auth.role() = 'service_role');
  END IF;
END $$;

-- ================================================
-- ⚠️  주의: RLS 적용 후 백엔드에서 service_role 키를 사용해야 함
-- Railway 환경변수: SUPABASE_SERVICE_KEY=eyJ... (service_role JWT)
-- db_supabase.py: create_client(url, service_role_key)
-- ================================================
