"""
schemas.py - Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from models import UserRole, OrderStatus


# ─── Auth Schemas ────────────────────────────────────────────────────────────

class UserSignup(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class TokenData(BaseModel):
    user_id: Optional[int] = None
    role: Optional[str] = None


# ─── User Schemas ─────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    avatar_url: Optional[str] = None


class AdminUserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None


# ─── Product Schemas ──────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = Field(None, max_length=500)
    price: float = Field(..., gt=0)
    original_price: Optional[float] = Field(None, gt=0)
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    is_featured: Optional[bool] = False


class ProductUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    original_price: Optional[float] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None


class ProductResponse(BaseModel):
    id: int
    title: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    original_price: Optional[float] = None
    thumbnail_url: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    is_active: bool
    is_featured: bool
    total_sales: int
    created_at: datetime

    class Config:
        from_attributes = True


class ProductDetailResponse(ProductResponse):
    """Extended product info — file_name shown but NOT file_url (protected)"""
    file_name: Optional[str] = None


# ─── Order Schemas ────────────────────────────────────────────────────────────

class CreateOrderRequest(BaseModel):
    product_ids: List[int] = Field(..., min_length=1)


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    price_at_purchase: float
    product: Optional[ProductResponse] = None

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    user_id: int
    total_amount: float
    status: OrderStatus
    razorpay_order_id: Optional[str] = None
    items: List[OrderItemResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Payment Schemas ──────────────────────────────────────────────────────────

class CreatePaymentOrder(BaseModel):
    product_ids: List[int]


class CreatePaymentOrderResponse(BaseModel):
    razorpay_order_id: str
    amount: int           # In paise (INR smallest unit)
    currency: str
    order_id: int         # Our internal order ID
    key_id: str           # Public Razorpay key for frontend


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    order_id: int         # Our internal order ID


class VerifyPaymentResponse(BaseModel):
    success: bool
    message: str
    order_id: Optional[int] = None


# ─── Download Schemas ─────────────────────────────────────────────────────────

class DownloadLinkResponse(BaseModel):
    download_url: str
    file_name: str
    expires_in: int       # Seconds until link expires


# ─── Admin / Analytics Schemas ────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_users: int
    total_products: int
    total_orders: int
    total_revenue: float
    recent_orders: List[OrderResponse] = []


# Update forward references
Token.model_rebuild()
