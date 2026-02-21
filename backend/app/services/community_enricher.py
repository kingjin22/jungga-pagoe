"""
커뮤니티 딜 정가(MSRP) 자동 탐지 및 유효성 검증

동작:
1. 제목으로 Naver Shopping 검색 → hprice(정가) 탐지
2. 식품/일상용품 카테고리 필터링 (금지)
3. 만료 키워드 감지 (원글 페이지 스캔)
"""
import re
import asyncio
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# ─── 식품/일상용품 금지 키워드 ───────────────────────────────────────────────
FOOD_TITLE_KEYWORDS = [
    # 육류/해산물
    "라면", "오징어", "새우", "참치", "햄", "소시지", "삼겹살", "닭고기",
    "돼지고기", "소고기", "갈비", "족발", "보쌈", "닭가슴살", "코다리",
    "황태", "명태", "고등어", "멸치", "홍합", "전복",
    # 가공식품/간편식
    "과자", "빵", "케이크", "초콜릿", "사탕", "젤리", "당면", "국수",
    "파스타", "즉석밥", "햇반", "컵라면", "떡", "떡볶이", "만두",
    "순대", "어묵", "소떡", "핫도그",
    # 유제품/음료
    "우유", "치즈", "요거트", "요구르트", "주스", "음료", "에너지드링크",
    "파워에이드", "게토레이", "콜라", "사이다", "맥주", "소주", "와인",
    "막걸리", "커피", "홍차", "녹차", "카페",
    # 채소/과일/곡류
    "쌀", "밀가루", "설탕", "소금", "식용유", "간장", "고추장", "된장",
    "김치", "두부", "콩나물", "감자", "고구마", "양파", "마늘",
    "수박", "포도", "딸기", "바나나", "망고", "복숭아", "사과", "배",
    "계란", "달걀", "김",
    # 건강기능식품
    "비타민", "유산균", "프로바이오틱스", "콜라겐", "오메가", "홍삼", "인삼",
    "멜라토닌", "루테인", "마그네슘", "이론샷", "단백질쉐이크",
    # 생활용품
    "기저귀", "물티슈", "세제", "샴푸", "린스", "바디워시", "치약", "칫솔",
    "화장지", "롤화장지", "키친타월", "비누", "락스", "청소", "생리대",
    "팬티라이너", "탐폰", "면봉",
    # 음식 완성품 / 조리법
    "치킨", "피자", "버거", "도시락", "김밥", "찜", "국", "탕", "찌개",
    # 음료/탄산 추가
    "캔음료", "탄산수", "스파클링", "매실", "솔의눈", "식혜", "수정과",
    "쉐이크", "프로틴", "두유", "요거트",
    # 세제/생활용품
    "세제", "캡슐세제", "액체세제", "섬유유연제", "주방세제", "청소용품",
    "치약", "칫솔", "구강청결", "샴푸", "린스", "컨디셔너",
    "화장지", "휴지", "물티슈", "마스크팩",
    # 기타 식품 추가
    "오트밀", "그래놀라", "시리얼", "젤리빈", "하리보", "포켓몬빵",
    # 달걀/계란류
    "특란", "왕란", "신선란", "유정란", "무항생제",
    # 밀키트/간편조리
    "밀키트", "간편식", "헬로키트", "오늘뭐먹", "쿠캣",
    # 한우/육류
    "한우", "와규", "샤브샤브", "전골", "대창", "곱창",
    # 치아위생 (치약/구강청결제)
    "칫솔모", "구강청결", "가글",
    # 아이스크림/빙과
    "아이스크림", "아이스바", "빙과", "설빙", "젤라또", "샤베트",
    "벤앤제리스", "하겐다즈", "배스킨", "나뚜루",
    # 건어물/수산물
    "닭발", "족발", "순살", "진미채", "오징어채", "쥐포", "건오징어", "황태채", "코다리채",
    "어포", "전어", "한치", "갈치", "조기", "삼치",
    # 한약재/과실차
    "오미자", "모과", "유자", "레몬", "생강", "당귀", "감초",
    "구기자", "복분자", "도라지", "둥굴레", "옥수수수염",
    # 양념/조미료
    "고춧가루", "참기름", "들기름", "올리브유", "식초", "굴소스",
    "케첩", "마요네즈", "머스타드", "소스", "드레싱",
    # 과자/빙과류
    "과자", "감자칩", "팝콘", "크래커", "비스킷", "쿠키", "마카롱",
    # 양파/채소/과일
    "양파", "대파", "파프리카", "브로콜리", "상추", "시금치",
    "블루베리", "체리", "키위", "자몽", "오렌지", "귤",
    # 쌀/잡곡
    "쌀", "현미", "잡곡", "찹쌀", "보리", "귀리",
    # 신선식품
    "신선", "유기농", "친환경", "무농약",
    # 추가 음료
    "아메리카노", "라떼", "카페라떼", "카푸치노", "프라푸치노",
    "에너지드링크", "몬스터", "레드불", "암바사", "포카리",
    # 감미료/조미료류
    "알룰로스", "에리스리톨", "자일리톨", "아스파탐", "스테비아",
    # 상품권/기프트카드 (금지)
    "기프트카드", "gift card", "상품권", "쿠폰",
]

FOOD_CATEGORY_KEYWORDS = ["식품", "음식", "음료", "주류", "건강식품", "유아식", "간편식", "신선식품"]

# ─── 딜 만료 감지 키워드 ─────────────────────────────────────────────────────
EXPIRY_KEYWORDS = [
    "종료되었습니다", "종료됐습니다", "딜이 종료", "핫딜종료", "마감되었",
    "품절되었", "품절입니다", "품절됐", "sold out", "soldout",
    "삭제된 게시물", "존재하지 않는", "찾을 수 없", "페이지를 찾을 수",
    "판매가 종료", "판매종료", "구매불가", "취소되었", "취소됐",
    "행사가 종료", "이벤트가 종료", "프로모션이 종료",
    "남은 수량 없", "재고 없", "재고없음",
]

# 뽐뿌 특이 종료 패턴
PPOMPPU_ENDED_PATTERNS = [
    r"품절[이가]?\s*됐\|품절이?\s*되었",
    r"핫딜\s*(종료|마감)",
    r"(딜|행사|이벤트)\s*(종료|마감)\s*됐",
]


def is_food_or_daily(title: str, category: str = "") -> bool:
    """식품/일상용품 여부 감지 → True면 금지"""
    t = title.lower()
    if any(kw in t for kw in FOOD_TITLE_KEYWORDS):
        return True
    if any(kw in (category or "") for kw in FOOD_CATEGORY_KEYWORDS):
        return True
    return False


async def lookup_msrp_from_naver(title: str, sale_price: int) -> Optional[dict]:
    """
    Naver Shopping API로 커뮤니티 딜 정가 탐지

    Returns:
        {"original_price": int, "discount_rate": float, "image_url": str|None}
        or None if not found / discount too low
    """
    import os, urllib.parse

    client_id = os.environ.get("NAVER_CLIENT_ID", "wHDtIpb0AI8X7RlUSBJP")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET", "oZZAfOcWU7")

    # 제목 전처리
    clean = title
    # 쇼핑몰 태그 제거 ([네이버], [쿠팡], [-토스] 등)
    clean = re.sub(r"\[[-\s]*[^\]]+\]", "", clean).strip()
    # 괄호 제거
    clean = re.sub(r"\(.*?\)", "", clean).strip()
    # 쇼핑몰 이름 제거 (제목 앞에 오는 경우)
    MALLS = ["옥션", "G마켓", "지마켓", "11번가", "쿠팡", "네이버", "토스", "위메프", "티몬", "SSG", "롯데온"]
    for mall in MALLS:
        clean = re.sub(rf"^{mall}\s*", "", clean).strip()
    # "1+1", "2+1", "N개입", "N팩" 등 수량 표현 제거
    clean = re.sub(r"\b\d+\+\d+\b|\b\d+개입\b|\b\d+팩\b|\b\d+세트\b", "", clean).strip()
    # 연속 공백 제거
    clean = re.sub(r"\s+", " ", clean).strip()[:40]

    if len(clean) < 3:
        return None

    query = urllib.parse.quote(clean)
    url = f"https://openapi.naver.com/v1/search/shop.json?query={query}&display=10&sort=sim"

    try:
        async with httpx.AsyncClient(timeout=8) as client:
            r = await client.get(url, headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
            })
            data = r.json()
    except Exception as e:
        logger.warning(f"[CommunityEnricher] Naver API 오류: {e}")
        return None

    items = data.get("items", [])
    if not items:
        return None

    candidates = []
    for item in items:
        lp = int(item.get("lprice", 0) or 0)
        hp = int(item.get("hprice", 0) or 0)
        if lp <= 0:
            continue
        # hprice가 있으면 Naver가 인증한 정가
        if hp > 0 and hp > lp:
            candidates.append((hp, lp, item))
        # hprice 없어도 sale_price보다 높은 lprice가 나오면 참고용으로 사용
        elif hp == 0 and lp > sale_price * 1.05:
            candidates.append((lp, sale_price, item))

    if not candidates:
        return None

    # 가장 신뢰도 높은 후보 선택 (hprice > sale_price 인 것 중 최빈값)
    valid = [(hp, lp, item) for (hp, lp, item) in candidates if hp > sale_price * 1.08]
    if not valid:
        return None

    # 중간값 기준 정가 선택
    valid.sort(key=lambda x: x[0])
    hp, lp, best_item = valid[len(valid) // 2]

    discount_rate = round((1 - sale_price / hp) * 100, 1)
    if discount_rate < 5:  # 5% 미만은 의미 없음
        return None

    # 이미지
    img = best_item.get("image", "")

    logger.info(f"[CommunityEnricher] MSRP 탐지: {clean[:30]} → 정가={hp:,} 할인={discount_rate}%")
    return {
        "original_price": hp,
        "discount_rate": discount_rate,
        "image_url": img,
        "naver_title": best_item.get("title", "").replace("<b>", "").replace("</b>", ""),
    }


async def check_deal_expired_from_url(url: str) -> tuple[bool, str]:
    """
    커뮤니티 원글 URL에서 만료 감지

    Returns: (is_expired: bool, reason: str)
    """
    if not url:
        return False, ""

    try:
        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; JunggaPagoe-bot/1.0)"},
        ) as client:
            r = await client.get(url)
            text = r.text.lower()
            status = r.status_code
    except Exception as e:
        logger.warning(f"[CommunityEnricher] URL 접근 실패 {url}: {e}")
        return False, ""

    # 404/삭제된 페이지
    if status == 404:
        return True, "페이지 없음(404)"

    # 만료 키워드 감지
    for kw in EXPIRY_KEYWORDS:
        if kw.lower() in text:
            return True, f"키워드감지:{kw}"

    # 뽐뿌 특이 패턴
    for pattern in PPOMPPU_ENDED_PATTERNS:
        if re.search(pattern, text):
            return True, f"패턴감지:{pattern[:20]}"

    # 뽐뿌 "이 게시물은 삭제" 패턴
    if "ppomppu.com" in url:
        if "삭제된 게시물" in r.text or "게시물이 없습니다" in r.text:
            return True, "뽐뿌-삭제됨"
        # 댓글에서 품절/종료 키워드 감지 (하단부 200자 내)
        tail = r.text[-2000:].lower()
        for kw in ["품절", "종료", "sold out", "마감"]:
            if tail.count(kw) >= 3:  # 3번 이상 → 확실히 종료
                return True, f"댓글종료:{kw}"

    return False, ""
