"""
routes/orders.py - Order history and secure file download
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from typing import List
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_user
import os

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("", response_model=List[schemas.OrderResponse])
def get_my_orders(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all orders for the current user."""
    orders = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product)
    ).filter(
        models.Order.user_id == current_user.id
    ).order_by(models.Order.created_at.desc()).all()

    return orders


# ⚠️ IMPORTANT: /download/ route PEHLE hona chahiye /{order_id} se
# Warna FastAPI "download" ko order_id samajh leta hai
@router.get("/download/{product_id}")
def download_product(
    product_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Secure download endpoint — verifies user has purchased the product
    before serving the file.
    """
    # Check user has paid for this product
    purchase = db.query(models.OrderItem).join(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == models.OrderStatus.paid,
        models.OrderItem.product_id == product_id
    ).first()

    if not purchase:
        raise HTTPException(
            status_code=403,
            detail="You have not purchased this product"
        )

    # Get product file
    product = db.query(models.Product).filter(
        models.Product.id == product_id,
        models.Product.is_active == True
    ).first()

    if not product or not product.file_url:
        raise HTTPException(
            status_code=404,
            detail="File not found for this product"
        )

    # Verify file exists on disk
    if not os.path.exists(product.file_url):
        raise HTTPException(
            status_code=404,
            detail="File not found on server"
        )

    return FileResponse(
        path=product.file_url,
        filename=product.file_name or "download",
        media_type="application/octet-stream"
    )


@router.get("/{order_id}", response_model=schemas.OrderResponse)
def get_order(
    order_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific order by ID."""
    order = db.query(models.Order).options(
        joinedload(models.Order.items).joinedload(models.OrderItem.product)
    ).filter(
        models.Order.id == order_id,
        models.Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
