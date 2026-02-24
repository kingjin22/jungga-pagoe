from fastapi import APIRouter
from fastapi.responses import Response
import app.db_supabase as db
from datetime import datetime, timezone

router = APIRouter(prefix="/feed", tags=["feed"])


@router.get("/rss", response_class=Response)
async def rss_feed():
    deals = db.get_deals(size=30, sort="latest")
    items_xml = deals.get("items", []) if isinstance(deals, dict) else []

    items = ""
    for d in items_xml:
        title = d.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url = d.get("product_url", "")
        desc = f"{d.get('discount_rate', 0):.0f}% 할인 | {d.get('sale_price', 0):,}원 → {d.get('original_price', 0):,}원"
        image = d.get("image_url", "")
        created = d.get("created_at", datetime.now(timezone.utc).isoformat())
        items += f"""
  <item>
    <title>{title}</title>
    <link>{url}</link>
    <description>{desc}</description>
    <pubDate>{created}</pubDate>
    <guid>{url}</guid>
    {f'<enclosure url="{image}" type="image/jpeg" />' if image else ""}
  </item>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>정가파괴 — 오늘의 핫딜</title>
    <link>https://jungga-pagoe.vercel.app</link>
    <description>정가 대비 할인율 높은 핫딜만 모아드립니다</description>
    <language>ko</language>
    <atom:link href="https://jungga-pagoe-production.up.railway.app/feed/rss" rel="self" type="application/rss+xml" />
    {items}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/rss+xml")


@router.get("/google", response_class=Response)
async def google_shopping_feed():
    """Google Merchant Center 상품 피드 (RSS 2.0 + g: namespace)"""
    deals = db.get_deals(size=100, sort="latest")
    items_xml = deals.get("items", []) if isinstance(deals, dict) else []

    items = ""
    for d in items_xml:
        if not d.get("sale_price") or not d.get("product_url"):
            continue
        title = d.get("title", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        url = d.get("product_url", "")
        image = d.get("image_url", "")
        price = f"{int(d.get('sale_price', 0))} KRW"
        cat = d.get("category", "기타")
        deal_id = d.get("id", "")
        items += f"""
  <item>
    <title>{title}</title>
    <link>https://jungga-pagoe.vercel.app/deal/{deal_id}</link>
    <g:id>{deal_id}</g:id>
    <g:price>{price}</g:price>
    <g:sale_price>{price}</g:sale_price>
    <g:availability>in_stock</g:availability>
    <g:condition>new</g:condition>
    <g:product_type>{cat}</g:product_type>
    {f"<g:image_link>{image}</g:image_link>" if image else ""}
  </item>"""

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>정가파괴 핫딜</title>
    <link>https://jungga-pagoe.vercel.app</link>
    <description>정가 대비 할인율 높은 핫딜 상품</description>
    {items}
  </channel>
</rss>"""
    return Response(content=xml, media_type="application/xml")
