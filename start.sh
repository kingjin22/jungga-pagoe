#!/bin/bash
# 정가파괴 - 개발 서버 시작 스크립트

echo "🔥 정가파괴 시작 중..."

# 백엔드
echo "📦 백엔드 시작 (http://localhost:8001)"
cd "$(dirname "$0")/backend"
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# 잠깐 대기
sleep 2

# 프론트엔드
echo "🎨 프론트엔드 시작 (http://localhost:3001)"
cd "$(dirname "$0")/frontend"
npm run dev -- --port 3001 &
FRONTEND_PID=$!

echo ""
echo "✅ 정가파괴 실행 중!"
echo "   🌐 사이트: http://localhost:3001"
echo "   📚 API 문서: http://localhost:8001/docs"
echo ""
echo "종료: Ctrl+C"

# 종료 시 프로세스 정리
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit 0" SIGINT SIGTERM
wait
