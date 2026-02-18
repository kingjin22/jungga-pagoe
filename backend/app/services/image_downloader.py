"""
이미지 다운로드 → 로컬 저장
frontend/public/images/deals/ 에 저장 후 /images/deals/xxx.jpg 경로 반환
Next.js public 폴더에서 직접 서빙 → 도메인 설정 / Referer 문제 없음
"""
import hashlib
import httpx
from pathlib import Path
from typing import Optional

# 저장 경로 (backend 기준 상대 경로)
SAVE_DIR = Path(__file__).resolve().parents[3] / "frontend" / "public" / "images" / "deals"
SAVE_DIR.mkdir(parents=True, exist_ok=True)

# 뽐뿌 CDN은 Referer 없으면 404
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.ppomppu.co.kr/",
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
}

ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE = 5 * 1024 * 1024  # 5MB


def _url_to_filename(url: str) -> str:
    """URL → 고유 파일명 (SHA256 앞 16자)"""
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in ALLOWED_EXTS:
        ext = ".jpg"
    h = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{h}{ext}"


async def download_image(url: str, timeout: float = 8.0) -> Optional[str]:
    """
    이미지 URL 다운로드 → 로컬 저장
    Returns: '/images/deals/xxx.jpg' (Next.js public 경로) or None
    """
    if not url or not url.startswith("http"):
        return None

    filename = _url_to_filename(url)
    local_path = SAVE_DIR / filename
    public_path = f"/images/deals/{filename}"

    # 이미 다운로드된 파일이면 재사용
    if local_path.exists() and local_path.stat().st_size > 100:
        return public_path

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers=HEADERS,
                timeout=timeout,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                return None

            content = resp.content
            if len(content) < 100:  # 빈 파일 방지
                return None
            if len(content) > MAX_SIZE:
                return None

            # Content-Type 체크
            ct = resp.headers.get("content-type", "")
            if ct and "image" not in ct and "octet-stream" not in ct:
                return None

            local_path.write_bytes(content)
            return public_path

    except Exception as e:
        print(f"  [이미지 다운로드 실패] {url[:60]}: {e}")
        return None


async def download_image_batch(urls: list[str]) -> dict[str, Optional[str]]:
    """여러 URL 동시 다운로드 (최대 5개씩 병렬)"""
    import asyncio
    results = {}
    for i in range(0, len(urls), 5):
        batch = urls[i:i+5]
        tasks = [download_image(u) for u in batch]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        for url, res in zip(batch, batch_results):
            results[url] = res if not isinstance(res, Exception) else None
    return results
