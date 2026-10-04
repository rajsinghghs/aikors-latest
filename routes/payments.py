"""
routes/payments.py - Razorpay payment flow & Webhooks
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_user
from payment.razorpay_handler import create_razorpay_order, verify_payment_signature
import os
import hmac
import hashlib
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/payments", tags=["Payments"])

@router.post("/create-order", response_model=schemas.CreatePaymentOrderResponse)
def create_payment_order(
    request: schemas.CreatePaymentOrder,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    products = db.query(models.Product).filter(
        models.Product.id.in_(request.product_ids),
        models.Product.is_active == True
    ).all()

    if len(products) != len(request.product_ids):
        raise HTTPException(status_code=404, detail="One or more products not found")

    existing_purchases = db.query(models.OrderItem).join(models.Order).filter(
        models.Order.user_id == current_user.id,
        models.Order.status == models.OrderStatus.paid,
        models.OrderItem.product_id.in_(request.product_ids)
    ).all()

    if existing_purchases:
        already_bought = [item.product_id for item in existing_purchases]
        raise HTTPException(
            status_code=400,
            detail=f"You already own product(s): {already_bought}"
        )

    total_amount = sum(p.price for p in products)

    order = models.Order(
        user_id=current_user.id,
        total_amount=total_amount,
        status=models.OrderStatus.pending
    )
    db.add(order)
    db.flush()

    for product in products:
        item = models.OrderItem(
            order_id=order.id,
            product_id=product.id,
            price_at_purchase=product.price
        )
        db.add(item)

    rz_order = create_razorpay_order(
        amount_inr=total_amount,
        receipt=f"order_{order.id}",
        notes={"user_id": str(current_user.id), "user_email": current_user.email}
    )

    order.razorpay_order_id = rz_order["id"]

    payment = models.Payment(
        order_id=order.id,
        razorpay_order_id=rz_order["id"],
        amount=total_amount,
        currency="INR",
        status="pending"
    )
    db.add(payment)
    db.commit()

    return schemas.CreatePaymentOrderResponse(
        razorpay_order_id=rz_order["id"],
        amount=rz_order["amount"],
        currency=rz_order["currency"],
        order_id=order.id,
        key_id=os.getenv("RAZORPAY_KEY_ID", "")
    )


@router.post("/verify", response_model=schemas.VerifyPaymentResponse)
def verify_payment(
    verification: schemas.VerifyPaymentRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    order = db.query(models.Order).filter(
        models.Order.id == verification.order_id,
        models.Order.user_id == current_user.id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == models.OrderStatus.paid:
        return schemas.VerifyPaymentResponse(
            success=True,
            message="Payment already verified",
            order_id=order.id
        )

    is_valid = verify_payment_signature(
        razorpay_order_id=verification.razorpay_order_id,
        razorpay_payment_id=verification.razorpay_payment_id,
        razorpay_signature=verification.razorpay_signature
    )

    if not is_valid:
        payment = db.query(models.Payment).filter(
            models.Payment.order_id == order.id
        ).first()
        if payment:
            payment.status = "failed"
        order.status = models.OrderStatus.failed
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Payment verification failed. Invalid signature."
        )

    order.status = models.OrderStatus.paid

    payment = db.query(models.Payment).filter(
        models.Payment.order_id == order.id
    ).first()
    if payment:
        payment.razorpay_payment_id = verification.razorpay_payment_id
        payment.razorpay_signature = verification.razorpay_signature
        payment.status = "captured"

    for item in order.items:
        product = db.query(models.Product).filter(
            models.Product.id == item.product_id
        ).first()
        if product:
            product.total_sales += 1

    db.commit()

    return schemas.VerifyPaymentResponse(
        success=True,
        message="Payment verified successfully",
        order_id=order.id
    )

# 🚀 FAANG LEVEL FIX: RAZORPAY WEBHOOK FOR PENDING PAYMENTS 🚀
@router.post("/webhook")
async def razorpay_webhook(request: Request, db: Session = Depends(get_db)):
    """Razorpay calls this silently in background when payment succeeds."""
    payload = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")

    # Security check: verify webhook signature
    expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, signature):
        raise HTTPException(status_code=400, detail="Invalid Webhook Signature")

    data = await request.json()
    
    # If the payment was captured successfully
    if data.get("event") == "payment.captured":
        payment_entity = data["payload"]["payment"]["entity"]
        razorpay_order_id = payment_entity["order_id"]
        razorpay_payment_id = payment_entity["id"]

        # Find payment by Razorpay Order ID
        payment_record = db.query(models.Payment).filter(models.Payment.razorpay_order_id == razorpay_order_id).first()
        if payment_record and payment_record.status != "captured":
            payment_record.status = "captured"
            payment_record.razorpay_payment_id = razorpay_payment_id
            
            # Find the actual order and mark as paid
            order = db.query(models.Order).filter(models.Order.id == payment_record.order_id).first()
            if order and order.status != models.OrderStatus.paid:
                order.status = models.OrderStatus.paid
                
                # Increment sales
                for item in order.items:
                    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
                    if product: 
                        product.total_sales += 1
            
            db.commit()
            
    return {"status": "ok"}