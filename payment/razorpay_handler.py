"""
payment/razorpay_handler.py - Razorpay order creation and payment verification
"""
import razorpay
import hmac
import hashlib
from fastapi import HTTPException
import os
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")


def get_razorpay_client():
    """Get authenticated Razorpay client."""
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=500,
            detail="Razorpay credentials not configured"
        )
    return razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_inr: float, receipt: str, notes: dict = None) -> dict:
    """
    Create a Razorpay order.
    Amount is in INR — converted to paise (×100) internally.
    Returns the Razorpay order object.
    """
    client = get_razorpay_client()
    amount_paise = int(amount_inr * 100)   # Convert to smallest currency unit

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "notes": notes or {},
        "payment_capture": 1                # Auto-capture payment
    }

    try:
        order = client.order.create(data=order_data)
        return order
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create Razorpay order: {str(e)}"
        )


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str
) -> bool:
    """
    Verify Razorpay payment signature using HMAC-SHA256.
    This is CRITICAL — always verify before marking payment as successful.
    """
    try:
        # The message to sign is: order_id + "|" + payment_id
        message = f"{razorpay_order_id}|{razorpay_payment_id}"
        expected_signature = hmac.new(
            RAZORPAY_KEY_SECRET.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, razorpay_signature)
    except Exception:
        return False
