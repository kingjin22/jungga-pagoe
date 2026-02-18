from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Enum
from sqlalchemy.sql import func
import enum
from app.database import Base


class DealSource(str, enum.Enum):
    COUPANG = "coupang"
    NAVER = "naver"
    COMMUNITY = "community"


class DealCategory(str, enum.Enum):
    ELECTRONICS = "전자기기"
    FASHION = "패션"
    FOOD = "식품"
    BEAUTY = "뷰티"
    HOME = "홈리빙"
    SPORTS = "스포츠"
    KIDS = "유아동"
    OTHER = "기타"


class DealStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"


class Deal(Base):
    __tablename__ = "deals"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    original_price = Column(Float, nullable=False)
    sale_price = Column(Float, nullable=False)
    discount_rate = Column(Float, nullable=False)  # 0-100
    image_url = Column(String(1000), nullable=True)
    product_url = Column(String(1000), nullable=False)
    affiliate_url = Column(String(1000), nullable=True)  # 쿠팡 파트너스 링크
    source = Column(Enum(DealSource), default=DealSource.COMMUNITY)
    category = Column(Enum(DealCategory), default=DealCategory.OTHER)
    status = Column(Enum(DealStatus), default=DealStatus.ACTIVE)
    upvotes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    is_hot = Column(Boolean, default=False)  # 핫딜 태그
    submitter_name = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
