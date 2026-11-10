"""
routes/products.py - Product listing, detail, and admin CRUD
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_user, get_current_admin, get_optional_user
import re
import os
import aiofiles
import uuid
from dotenv import load_dotenv

# NAYA IMPORT: Cloudflare R2 function (generate_presigned_upload_url added)
try:
    from utils.r2_storage import upload_file_to_r2, generate_presigned_upload_url
except ImportError:
    upload_file_to_r2 = None
    generate_presigned_upload_url = None

load_dotenv()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
try:
    os.makedirs(f"{UPLOAD_DIR}/thumbnails", exist_ok=True)
    os.makedirs(f"{UPLOAD_DIR}/previews", exist_ok=True)
    os.makedirs(f"{UPLOAD_DIR}/files", exist_ok=True)
except OSError:
    # Vercel Read-Only Filesystem Fix
    UPLOAD_DIR = "/tmp/uploads"
    os.makedirs(f"{UPLOAD_DIR}/thumbnails", exist_ok=True)
    os.makedirs(f"{UPLOAD_DIR}/previews", exist_ok=True)
    os.makedirs(f"{UPLOAD_DIR}/files", exist_ok=True)

router = APIRouter(prefix="/products", tags=["Products"])

def make_slug(title: str) -> str:
    """Convert title to URL-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = re.sub(r'^-+|-+$', '', slug)
    return slug

# --- INLINE SCHEMAS FOR DIRECT UPLOAD ---
class UploadUrlRequest(BaseModel):
    filename: str
    content_type: str
    type: str

class ConfirmUploadRequest(BaseModel):
    file_url: str
    file_name: str
    type: str
    caption: Optional[str] = None
    thumb_url: Optional[str] = None


# ─── Public Endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=List[schemas.ProductResponse])
def list_products(
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all active products with optional filtering."""
    query = db.query(models.Product).options(
        selectinload(models.Product.reviews)
    ).filter(models.Product.is_active == True)

    if category:
        query = query.filter(func.lower(models.Product.category) == category.lower())
    if featured is not None:
        query = query.filter(models.Product.is_featured == featured)
    if search:
        query = query.filter(
            or_(
                models.Product.title.ilike(f"%{search}%"),
                models.Product.description.ilike(f"%{search}%"),
                models.Product.tags.ilike(f"%{search}%"),
            )
        )
    return query.order_by(models.Product.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/{slug}", response_model=schemas.ProductDetailResponse)
def get_product(slug: str, db: Session = Depends(get_db)):
    """Get a single product by slug."""
    product = db.query(models.Product).options(
        selectinload(models.Product.reviews),
        selectinload(models.Product.screenshots),
    ).filter(
        models.Product.slug == slug,
        models.Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.screenshots.sort(key=lambda shot: shot.sort_order or 0)
    return product


def _active_product(slug: str, db: Session) -> models.Product:
    product = db.query(models.Product).filter(
        models.Product.slug == slug,
        models.Product.is_active == True,
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def _review_payload(review: models.Review, buyers: set) -> schemas.ReviewResponse:
    name = (review.author_name or "").strip()
    if not name and review.user:
        name = review.user.name
    return schemas.ReviewResponse(
        id=review.id,
        user_id=review.user_id,
        user_name=name or "Student",
        rating=review.rating,
        comment=review.comment or "",
        verified_purchase=bool(review.user_id and review.user_id in buyers),
        is_visible=bool(review.is_visible),
        created_at=review.created_at,
    )


def _buyer_ids(product_id: int, db: Session) -> set:
    rows = db.query(models.Order.user_id).join(models.OrderItem).filter(
        models.OrderItem.product_id == product_id,
        models.Order.status == models.OrderStatus.paid,
    ).all()
    return {row[0] for row in rows}


@router.get("/{slug}/reviews", response_model=schemas.ReviewListResponse)
def list_reviews(
    slug: str,
    db: Session = Depends(get_db),
    user: Optional[models.User] = Depends(get_optional_user),
):
    """Public reviews for a product, with a 1–5 star breakdown."""
    product = _active_product(slug, db)
    reviews = db.query(models.Review).options(
        selectinload(models.Review.user)
    ).filter(
        models.Review.product_id == product.id,
        models.Review.is_visible.is_(True),
    ).order_by(models.Review.created_at.desc()).all()
    if user:
        mine_row = db.query(models.Review).options(
            selectinload(models.Review.user)
        ).filter(
            models.Review.product_id == product.id,
            models.Review.user_id == user.id,
        ).first()
        if mine_row and all(row.id != mine_row.id for row in reviews):
            reviews.append(mine_row)
    buyers = _buyer_ids(product.id, db)
    payload = [_review_payload(review, buyers) for review in reviews]
    visible_items = [item for item in payload if item.is_visible]
    breakdown = {str(star): 0 for star in range(1, 6)}
    for item in visible_items:
        key = str(item.rating)
        if key in breakdown:
            breakdown[key] += 1
    average = round(sum(item.rating for item in visible_items) / len(visible_items), 1) if visible_items else None
    mine = next((item for item in payload if user and item.user_id == user.id), None)
    return schemas.ReviewListResponse(
        average=average,
        count=len(visible_items),
        breakdown=breakdown,
        purchased=bool(user and user.id in buyers),
        my_review_id=mine.id if mine else None,
        reviews=payload,
    )


@router.post("/{slug}/reviews", response_model=schemas.ReviewResponse)
def upsert_review(
    slug: str,
    body: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Create or update the signed-in user's review. One review per product."""
    product = _active_product(slug, db)
    comment = (body.comment or "").strip()
    if comment and len(comment) < 2:
        raise HTTPException(status_code=400, detail="Write at least 2 characters, or leave the comment empty")

    review = db.query(models.Review).filter(
        models.Review.product_id == product.id,
        models.Review.user_id == user.id,
    ).first()
    if review:
        review.rating = body.rating
        review.comment = comment
    else:
        review = models.Review(
            product_id=product.id,
            user_id=user.id,
            rating=body.rating,
            comment=comment,
        )
        db.add(review)
    db.commit()
    db.refresh(review)
    verified = user.id in _buyer_ids(product.id, db)
    return _review_payload(review, {user.id} if verified else set())


@router.delete("/{slug}/reviews/mine", status_code=204)
def delete_my_review(
    slug: str,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
):
    """Remove the signed-in user's review."""
    product = _active_product(slug, db)
    review = db.query(models.Review).filter(
        models.Review.product_id == product.id,
        models.Review.user_id == user.id,
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()


# ─── Admin Endpoints ──────────────────────────────────────────────────────────

@router.post("", response_model=schemas.ProductResponse, status_code=201)
def create_product(
    product_data: schemas.ProductCreate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Create a new product."""
    base_slug = make_slug(product_data.title)
    slug = base_slug
    counter = 1
    while db.query(models.Product).filter(models.Product.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    product = models.Product(
        **product_data.model_dump(),
        slug=slug
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=schemas.ProductResponse)
def update_product(
    product_id: int,
    update_data: schemas.ProductUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Update a product."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Soft-delete a product."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()


# 🚀 NAYA: VERCEL 413 BYPASS DIRECT UPLOAD URL
@router.post("/{product_id}/get-upload-url")
def get_upload_url(product_id: int, req: UploadUrlRequest, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    if not generate_presigned_upload_url:
        raise HTTPException(status_code=500, detail="R2 Storage not configured")
    if req.type == "thumbnail":
        folder = "thumbnails"
    elif req.type == "screenshot":
        folder = "previews"
    else:
        folder = "files"
    data = generate_presigned_upload_url(folder, req.filename, req.content_type)
    return data

@router.post("/{product_id}/confirm-upload")
def confirm_upload(product_id: int, req: ConfirmUploadRequest, db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    shot = None
    if req.type == "thumbnail":
        product.thumbnail_url = req.file_url
    elif req.type == "screenshot":
        next_order = db.query(models.ProductScreenshot).filter(
            models.ProductScreenshot.product_id == product.id
        ).count()
        shot = models.ProductScreenshot(
            product_id=product.id,
            image_url=req.file_url,
            thumb_url=req.thumb_url or None,
            caption=(req.caption or req.file_name or "Preview")[:200],
            sort_order=next_order,
        )
        db.add(shot)
    else:
        product.file_url = req.file_url
        product.file_name = req.file_name
    db.commit()
    if shot is not None:
        db.refresh(shot)
        return {
            "success": True,
            "id": shot.id,
            "image_url": shot.image_url,
            "thumb_url": shot.thumb_url,
            "caption": shot.caption,
        }
    return {"success": True}


@router.delete("/{product_id}/screenshots/{screenshot_id}", status_code=204)
def delete_screenshot(
    product_id: int,
    screenshot_id: int,
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    """Admin: remove a public preview image."""
    shot = db.query(models.ProductScreenshot).filter(
        models.ProductScreenshot.id == screenshot_id,
        models.ProductScreenshot.product_id == product_id,
    ).first()
    if not shot:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    db.delete(shot)
    db.commit()


# ─── FALLBACK UPLOAD ROUTES (If R2 is missing) ────────────────────────────────────────

@router.post("/{product_id}/upload-file")
async def upload_product_file(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    product.file_name = file.filename

    if upload_file_to_r2 and os.getenv('R2_ACCESS_KEY_ID'):
        try:
            r2_path = upload_file_to_r2(file_content=content, original_filename=file.filename, folder="files", content_type=file.content_type)
            product.file_url = r2_path
            db.commit()
            return {"message": "File uploaded successfully to Cloudflare R2", "file_name": file.filename}
        except Exception as e:
            print(f"R2 Upload failed, falling back to local storage: {e}")

    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"{UPLOAD_DIR}/files/{unique_name}"
    async with aiofiles.open(file_path, 'wb') as f: await f.write(content)
    product.file_url = file_path
    db.commit()
    return {"message": "File uploaded successfully to Local Storage", "file_name": file.filename}


@router.post("/{product_id}/upload-thumbnail")
async def upload_thumbnail(product_id: int, file: UploadFile = File(...), db: Session = Depends(get_db), admin: models.User = Depends(get_current_admin)):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product: raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    if upload_file_to_r2 and os.getenv('R2_ACCESS_KEY_ID'):
        try:
            thumbnail_url = upload_file_to_r2(file_content=content, original_filename=file.filename, folder="thumbnails", content_type=file.content_type)
            product.thumbnail_url = thumbnail_url
            db.commit()
            return {"thumbnail_url": product.thumbnail_url, "source": "R2"}
        except Exception as e:
            print(f"R2 Thumbnail Upload failed, falling back to local: {e}")

    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"{UPLOAD_DIR}/thumbnails/{unique_name}"
    async with aiofiles.open(file_path, 'wb') as f: await f.write(content)
    product.thumbnail_url = f"/uploads/thumbnails/{unique_name}"
    db.commit()
    return {"thumbnail_url": product.thumbnail_url, "source": "Local"}


def _store_preview_bytes(content: bytes, filename: str, content_type: str):
    if upload_file_to_r2 and os.getenv("R2_ACCESS_KEY_ID"):
        try:
            return upload_file_to_r2(
                file_content=content,
                original_filename=filename,
                folder="previews",
                content_type=content_type,
            )
        except Exception as exc:
            print(f"R2 screenshot upload failed, falling back to local: {exc}")
    ext = os.path.splitext(filename or "")[1] or ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"{UPLOAD_DIR}/previews/{unique_name}"
    with open(file_path, "wb") as handle:
        handle.write(content)
    return f"/uploads/previews/{unique_name}"


@router.post("/{product_id}/upload-screenshot")
async def upload_screenshot(
    product_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin),
):
    """Admin: add a public content preview. A small copy is stored for the page grid."""
    from utils.image_preview import preview_variants

    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty image")
    full_bytes, thumb_bytes, prepared_type = preview_variants(content)
    content_type = prepared_type or file.content_type or "image/jpeg"
    filename = file.filename or "preview.jpg"
    if prepared_type == "image/jpeg":
        filename = os.path.splitext(filename)[0] + ".jpg"

    image_url = _store_preview_bytes(full_bytes, filename, content_type)
    thumb_url = image_url
    if thumb_bytes != full_bytes:
        thumb_url = _store_preview_bytes(thumb_bytes, "thumb-" + filename, content_type)

    next_order = db.query(models.ProductScreenshot).filter(
        models.ProductScreenshot.product_id == product.id
    ).count()
    shot = models.ProductScreenshot(
        product_id=product.id,
        image_url=image_url,
        thumb_url=thumb_url,
        caption=(caption or file.filename or "Preview")[:200],
        sort_order=next_order,
    )
    db.add(shot)
    db.commit()
    db.refresh(shot)
    return {
        "id": shot.id,
        "image_url": shot.image_url,
        "thumb_url": shot.thumb_url,
        "caption": shot.caption,
    }