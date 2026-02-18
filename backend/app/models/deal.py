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
    EXPIRED = "expired"       # 가격 올라가거나 딜 종료
    PENDING = "pending"       # 검토 대기 (추후 활용)
    PRICE_CHANGED = "price_changed"  # 가격 변동 감지됨


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
    affiliate_url = Column(String(1000), nullable=True)
    source = Column(Enum(DealSource), default=DealSource.COMMUNITY)
    category = Column(Enum(DealCategory), default=DealCategory.OTHER)
    status = Column(Enum(DealStatus), default=DealStatus.ACTIVE)
    upvotes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    is_hot = Column(Boolean, default=False)
    submitter_name = Column(String(100), nullable=True)
    expires_at = Column(DateTime, nullable=True)

    # 가격 검증 필드
    verified_price = Column(Float, nullable=True)       # 마지막으로 확인된 실제 가격
    last_verified_at = Column(DateTime, nullable=True)  # 마지막 검증 시각
    verify_fail_count = Column(Integer, default=0)      # 연속 검증 실패 횟수

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
