-- site_settings: 서비스 전체 설정 KV 스토어
CREATE TABLE IF NOT EXISTS site_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS: 서비스 역할(backend)만 읽기/쓰기
ALTER TABLE site_settings ENABLE ROW LEVEL SECURITY;

-- anon은 읽기만 가능 (선택사항, 민감한 키는 SELECT 금지 처리)
CREATE POLICY "service_read" ON site_settings
  FOR SELECT USING (true);

CREATE POLICY "service_write" ON site_settings
  FOR ALL USING (auth.role() = 'service_role');

-- 초기값 삽입 (토큰은 나중에 /admin/update-coupang-token으로 갱신)
INSERT INTO site_settings (key, value) VALUES
  ('coupang_partners_token', ''),
  ('coupang_partners_cookie', '')
ON CONFLICT (key) DO NOTHING;
