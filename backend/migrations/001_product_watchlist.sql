-- product_watchlist: 인기 제품 가격 추적 워치리스트
CREATE TABLE IF NOT EXISTS product_watchlist (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,           -- 표시 이름 (예: "나이키 페가수스 41")
    search_query    TEXT NOT NULL,           -- Naver 검색어
    category        TEXT DEFAULT '기타',
    brand           TEXT,
    msrp            INTEGER DEFAULT 0,       -- 권장소비자가 (0이면 hprice 자동 기준)
    alert_threshold INTEGER DEFAULT 15,      -- 평균 대비 하락 % 기준
    min_price       INTEGER DEFAULT 0,       -- 이 가격 미만은 가품 의심 → 스킵
    current_lprice  INTEGER DEFAULT 0,       -- 현재 Naver 최저가 (캐시)
    avg_30d_lprice  INTEGER DEFAULT 0,       -- 30일 평균 최저가
    last_checked_at TIMESTAMPTZ,
    is_active       BOOLEAN DEFAULT true,
    source          TEXT DEFAULT 'manual',   -- 'manual' | 'kream'
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 가격 이력 로그 (30일 rolling)
CREATE TABLE IF NOT EXISTS watchlist_price_log (
    id              SERIAL PRIMARY KEY,
    watchlist_id    INTEGER REFERENCES product_watchlist(id) ON DELETE CASCADE,
    lprice          INTEGER NOT NULL,
    hprice          INTEGER,
    checked_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wplog_id_checked
    ON watchlist_price_log(watchlist_id, checked_at DESC);

-- RLS 비활성화 (서비스 전용)
ALTER TABLE product_watchlist DISABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist_price_log DISABLE ROW LEVEL SECURITY;
