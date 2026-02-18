from pydantic import BaseModel, HttpUrl, validator
from typing import Optional
from datetime import datetime
from app.models.deal import DealSource, DealCategory, DealStatus


class DealBase(BaseModel):
    title: str
    description: Optional[str] = None
    original_price: float
    sale_price: float
    image_url: Optional[str] = None
    product_url: str
    category: DealCategory = DealCategory.OTHER
    source: DealSource = DealSource.COMMUNITY


class DealCreate(DealBase):
    submitter_name: Optional[str] = None
    affiliate_url: Optional[str] = None
    expires_at: Optional[datetime] = None

    @validator("sale_price")
    def sale_must_be_less_than_original(cls, v, values):
        if "original_price" in values and v >= values["original_price"]:
            raise ValueError("판매가는 원가보다 낮아야 합니다")
        return v


class DealUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    original_price: Optional[float] = None
    sale_price: Optional[float] = None
    status: Optional[DealStatus] = None
    is_hot: Optional[bool] = None


class DealResponse(DealBase):
    id: int
    discount_rate: float
    affiliate_url: Optional[str] = None
    status: DealStatus
    upvotes: int
    views: int
    is_hot: bool
    submitter_name: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DealListResponse(BaseModel):
    items: list[DealResponse]
    total: int
    page: int
    size: int
    pages: int


class DealSubmitCommunity(BaseModel):
    """커뮤니티 딜 제보용 스키마"""
    title: str
    original_price: float
    sale_price: float
    product_url: str
    image_url: Optional[str] = None
    category: DealCategory = DealCategory.OTHER
    description: Optional[str] = None
    submitter_name: Optional[str] = "익명"
