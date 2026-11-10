
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session, joinedload, selectinload
from datetime import datetime, timedelta
from sqlalchemy import cast, Date
from sqlalchemy import func, or_ , String
from typing import List, Optional, Any
from pydantic import BaseModel
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_admin

# Password hashing ke liye (Aapka jo bhi existing hash setup ho, usse replace kar sakte hain, standard passlib use kiya hai)
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/admin", tags=["Admin"])


# ─── INLINE SCHEMAS FOR ADMIN ACTIONS (Bypass editing schemas.py) ─────────────
class AdminPasswordReset(BaseModel):
    new_password: str

class AdminOrderUpdate(BaseModel):
    status: models.OrderStatus

class AdminProductUpdate(BaseModel):
    title: Optional[str] = None
    price: Optional[float] = None
    total_sales: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin dashboard with FAANG level platform analytics & daily charts."""
    today = datetime.utcnow().date()
    
    total_users = db.query(models.User).count()
    total_products = db.query(models.Product).filter(models.Product.is_active == True).count()
    
    # All Time Orders & Revenue
    all_paid_orders = db.query(models.Order).filter(models.Order.status == models.OrderStatus.paid).all()
    total_orders = len(all_paid_orders)
    total_revenue = sum(o.total_amount for o in all_paid_orders)

    # Today's Orders & Revenue (Resets automatically every day)
    today_orders_query = db.query(models.Order).filter(
        models.Order.status == models.OrderStatus.paid,
        cast(models.Order.created_at, Date) == today
    ).all()
    today_orders = len(today_orders_query)
    today_revenue = sum(o.total_amount for o in today_orders_query)

    # Last 7 Days Revenue for Chart
    chart_labels = []
    chart_data = []
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        day_orders = db.query(models.Order).filter(
            models.Order.status == models.OrderStatus.paid,
            cast(models.Order.created_at, Date) == target_date
        ).all()
        chart_labels.append(target_date.strftime("%a")) # Mon, Tue, etc.
        chart_data.append(sum(o.total_amount for o in day_orders))

    # Last 10 paid orders with Users & Items loaded
    recent_orders = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product),
        joinedload(models.Order.user)
    ).filter(
        models.Order.status == models.OrderStatus.paid
    ).order_by(models.Order.created_at.desc()).limit(10).all()

    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "today_orders": today_orders,
        "today_revenue": today_revenue,
        "chart": {
            "labels": chart_labels,
            "data": chart_data
        },
        "recent_orders": recent_orders
    }

# ─── 1. USERS CONTROLS & 360-VIEW ─────────────────────────────────────────────

@router.get("/users")
def list_users(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: List all users with deep search capability."""
    query = db.query(models.User)
    
    # Deep Search Implementation
    if search:
        query = query.filter(
            or_(
                models.User.name.ilike(f"%{search}%"),
                models.User.email.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    users = query.order_by(models.User.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"total": total, "items": users}


@router.get("/users/{user_id}/details")
def get_user_details(user_id: int, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    # 🚀 FIX: Eager load (JOIN) Order Items and Products
    orders = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product)
    ).filter(models.Order.user_id == user_id).order_by(models.Order.created_at.desc()).all()
    
    total_spent = sum(o.total_amount for o in orders if o.status == models.OrderStatus.paid)
    
    return {
        "user_info": user,
        "total_spent": total_spent,
        "total_orders_count": len(orders),
        "order_history": orders
    }


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    update_data: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Update any user's details (Block/Unblock, Change Role)."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/force-password")
def force_change_password(
    user_id: int,
    data: AdminPasswordReset,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin Supreme Control: Force change any user's password without email."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.hashed_password = pwd_context.hash(data.new_password)
    db.commit()
    return {"success": True, "message": f"Password updated successfully for {user.email}"}


# ─── 2. ORDERS CONTROLS ───────────────────────────────────────────────────────

@router.get("/orders")
def list_all_orders(
    search: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: View all orders with search (by Razorpay ID or User Email) and filters."""
    query = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product),
        joinedload(models.Order.user)
    )
    
    if status:
        query = query.filter(models.Order.status == status)
        
    if search:
        query = query.join(models.User).filter(
            or_(
                models.Order.razorpay_order_id.ilike(f"%{search}%"),
                models.User.email.ilike(f"%{search}%")
            )
        )

    total = query.count()
    orders = query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()
    
    return {"total": total, "items": orders}


@router.patch("/orders/{order_id}")
def update_order_status(
    order_id: int,
    data: AdminOrderUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin Control: Manually update order status (e.g., pending to paid/refunded)."""
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.status = data.status
    db.commit()
    db.refresh(order)
    return {"success": True, "message": f"Order {order_id} status changed to {data.status}", "order": order}


# ─── 3. PRODUCTS CONTROLS ─────────────────────────────────────────────────────

@router.get("/products")
def list_all_products(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: List all products with search capabilities."""
    query = db.query(models.Product)
    
    if search:
        query = query.filter(models.Product.title.ilike(f"%{search}%"))
        
    total = query.count()
    products = query.options(
        selectinload(models.Product.screenshots)
    ).order_by(models.Product.created_at.desc()).offset(skip).limit(limit).all()

    items = []
    for product in products:
        items.append({
            "id": product.id,
            "title": product.title,
            "slug": product.slug,
            "description": product.description,
            "short_description": product.short_description,
            "price": product.price,
            "original_price": product.original_price,
            "thumbnail_url": product.thumbnail_url,
            "file_name": product.file_name,
            "category": product.category,
            "tags": product.tags,
            "is_active": product.is_active,
            "is_featured": product.is_featured,
            "total_sales": product.total_sales,
            "screenshots": [
                {
                    "id": shot.id,
                    "image_url": shot.image_url,
                    "caption": shot.caption,
                    "sort_order": shot.sort_order,
                }
                for shot in sorted(product.screenshots, key=lambda shot: shot.sort_order or 0)
            ],
        })

    return {"total": total, "items": items}


@router.put("/products/{product_id}")
def update_product_admin(
    product_id: int,
    update_data: AdminProductUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin Control: Manipulate product details, prices, and fake/real sales numbers."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return {"success": True, "product": product}
    total_users = db.query(func.count(models.User.id)).scalar()
    total_products = db.query(func.count(models.Product.id)).filter(
        models.Product.is_active == True
    ).scalar()
    total_orders = db.query(func.count(models.Order.id)).filter(
        models.Order.status == models.OrderStatus.paid
    ).scalar()
    total_revenue = db.query(func.sum(models.Order.total_amount)).filter(
        models.Order.status == models.OrderStatus.paid
    ).scalar() or 0.0

    # Last 10 paid orders
    recent_orders = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product),
        joinedload(models.Order.user)
    ).filter(
        models.Order.status == models.OrderStatus.paid
    ).order_by(models.Order.created_at.desc()).limit(10).all()

    return schemas.DashboardStats(
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        recent_orders=recent_orders
    )


@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: List all users."""
    return db.query(models.User).offset(skip).limit(limit).all()


@router.put("/users/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: int,
    update_data: schemas.AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Update any user's details."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user

@router.patch("/users/{user_id}/role")
def change_user_role(user_id: int, role_data: dict, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user: raise HTTPException(status_code=404, detail="User not found")
    
    # 🚀 Security Check: Admin khud ka role change na kar paye galti se!
    if user.id == admin.id and role_data.get("role") == "user":
        raise HTTPException(status_code=400, detail="You cannot revoke your own admin rights.")

    new_role = role_data.get("role")
    if new_role == "admin":
        user.role = models.UserRole.admin
    elif new_role == "user":
        user.role = models.UserRole.user
    else:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    db.commit()
    return {"message": f"User role updated successfully"}

@router.get("/orders", response_model=List[schemas.OrderResponse])
def list_all_orders(
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: View all orders across all users."""
    query = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product),
        joinedload(models.Order.user)
    )
    if status:
        query = query.filter(models.Order.status == status)

    return query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()


# ─── 5. PAYMENTS (FULL LIST) ─────────────────────────────────────────

@router.get("/payments")
def get_all_payments(skip: int = 0, limit: int = 20, search: Optional[str] = None, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    query = db.query(models.Payment)
    if search:
        query = query.filter(or_(
            models.Payment.razorpay_payment_id.ilike(f"%{search}%"),
            models.Payment.razorpay_order_id.ilike(f"%{search}%"),
            cast(models.Payment.order_id, String).ilike(f"%{search}%")  # 🚀 FIX: Used SQLAlchemy String
        ))
    total = query.count()
    items = query.order_by(models.Payment.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": items}


@router.get("/products", response_model=List[schemas.ProductDetailResponse])
def list_all_products(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: List all products including inactive ones."""
    return db.query(models.Product).order_by(
        models.Product.created_at.desc()
    ).offset(skip).limit(limit).all()
