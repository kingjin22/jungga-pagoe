# 정가파괴 (JungGa-Pagoe) 🔥

쿠팡/네이버 핫딜 자동 수집 + 커뮤니티 제보 플랫폼

## 기술 스택

- **Backend:** FastAPI + SQLite (SQLAlchemy) + APScheduler
- **Frontend:** Next.js 14 + Tailwind CSS v4
- **수익화:** 쿠팡 파트너스 제휴 링크 자동 변환

## 실행 방법

```bash
./start.sh
```

또는 수동 실행:

```bash
# Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --port 8001 --reload

# Frontend
cd frontend
npm run dev
```

## API 키 설정 (.env)

`backend/.env` 파일 생성:

```env
COUPANG_ACCESS_KEY=your_access_key
COUPANG_SECRET_KEY=your_secret_key
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

- 쿠팡 파트너스: https://partners.coupang.com
- 네이버 오픈API: https://developers.naver.com

## 주요 기능

- 🛒 **쿠팡/네이버 핫딜 자동 수집** (30분/1시간 간격)
- 👥 **커뮤니티 딜 제보** (추천 10개 → 🔥 HOT 태그 자동 부여)
- 🔗 **쿠팡 파트너스 링크 자동 변환** (수익화)
- 🔍 **카테고리/정렬/검색 필터**
- 📊 **실시간 통계** (총 딜, 핫딜, 평균 할인율)
- 🎨 **딜 상세 모달** (클릭 시 팝업)
- 📱 **반응형 디자인** (모바일 최적화)

## API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| GET | `/api/deals` | 딜 목록 (필터/정렬/검색) |
| GET | `/api/deals/hot` | 핫딜 TOP 10 |
| GET | `/api/deals/{id}` | 딜 상세 |
| POST | `/api/deals/{id}/upvote` | 딜 추천 |
| POST | `/api/deals/submit` | 커뮤니티 딜 제보 |
| POST | `/api/deals/sync/coupang` | 쿠팡 딜 수동 sync |
| POST | `/api/deals/sync/naver` | 네이버 딜 수동 sync |
| PATCH | `/api/deals/{id}/expire` | 딜 만료 처리 |
| GET | `/api/stats` | 통계 조회 |
| GET | `/docs` | Swagger UI |

## 폴더 구조

```
jungga-pagoe/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI 앱 + 시드 데이터
│   │   ├── scheduler.py     # APScheduler 자동 sync
│   │   ├── config.py        # 환경 변수
│   │   ├── database.py      # SQLAlchemy 설정
│   │   ├── models/          # DB 모델
│   │   ├── routers/         # API 라우터
│   │   │   ├── deals.py
│   │   │   └── stats.py
│   │   ├── schemas/         # Pydantic 스키마
│   │   └── services/        # 외부 API 서비스
│   │       ├── coupang.py
│   │       └── naver.py
│   └── requirements.txt
└── frontend/
    ├── app/
    │   ├── page.tsx          # 메인 페이지
    │   ├── layout.tsx
    │   ├── globals.css
    │   └── submit/page.tsx   # 딜 제보 페이지
    ├── components/
    │   ├── Header.tsx        # 헤더 + 검색
    │   ├── DealCard.tsx      # 딜 카드
    │   ├── DealModal.tsx     # 딜 상세 모달
    │   ├── DealSkeleton.tsx  # 로딩 스켈레톤
    │   ├── StatsBar.tsx      # 통계 바
    │   ├── HotBanner.tsx     # 핫딜 배너
    │   └── SortBar.tsx       # 정렬 바
    └── lib/
        └── api.ts            # API 클라이언트
```
