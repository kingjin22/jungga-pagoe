from pydantic import BaseModel, validator
from typing import Optional
from datetime import datetime


class DealBase(BaseModel):
    title: str
    description: Optional[str] = None
    original_price: float
    sale_price: float
    image_url: Optional[str] = None
    product_url: str
    category: str = "기타"   # 자유 텍스트 — enum 아님
    source: str = "community"


class DealCreate(DealBase):
    submitter_name: Optional[str] = None
    affiliate_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    @validator("sale_price")
    def sale_must_be_less_than_original(cls, v, values):
        if "original_price" in values and v >= values["original_price"]:
            raise ValueError("판매가는 원가보다 낮아야 합니다")
        return v


class DealResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    original_price: float
    sale_price: float
    discount_rate: float
    image_url: Optional[str] = None
    product_url: str
    affiliate_url: Optional[str] = None
    source: str
    category: str
    status: str
    upvotes: int
    views: int
    is_hot: bool
    submitter_name: Optional[str] = None
    expires_at: Optional[str] = None
    verified_price: Optional[float] = None
    last_verified_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DealListResponse(BaseModel):
    items: list[DealResponse]
    total: int
    page: int
    size: int
    pages: int


class DealSubmitCommunity(BaseModel):
    """커뮤니티 딜 제보 — 카테고리 자유 입력"""
    title: str
    original_price: float
    sale_price: float
    product_url: str
    image_url: Optional[str] = None
    category: Optional[str] = None   # 없으면 타이틀로 자동 추론
    description: Optional[str] = None
    submitter_name: Optional[str] = "익명"
