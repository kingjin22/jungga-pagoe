-- site_settings: 서비스 전체 설정 KV 스토어
CREATE TABLE IF NOT EXISTS site_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS 비활성화 (백엔드 서버에서만 접근, 브라우저 직접 접근 없음)
-- 민감 키가 있으면 서비스롤 키로 업그레이드 고려
ALTER TABLE site_settings DISABLE ROW LEVEL SECURITY;

-- 초기값 삽입 (토큰은 나중에 /admin/update-coupang-token으로 갱신)
INSERT INTO site_settings (key, value) VALUES
  ('coupang_partners_token', ''),
  ('coupang_partners_cookie', '')
ON CONFLICT (key) DO NOTHING;
