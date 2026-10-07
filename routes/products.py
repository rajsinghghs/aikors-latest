"""
routes/products.py - Product listing, detail, and admin CRUD
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from typing import List, Optional
from database import get_db
import models
import schemas
from auth.jwt_handler import get_current_user, get_current_admin, get_optional_user
import re
import os
import aiofiles
import uuid
from dotenv import load_dotenv

# NAYA IMPORT: Cloudflare R2 function
try:
    from utils.r2_storage import upload_file_to_r2
except ImportError:
    upload_file_to_r2 = None

load_dotenv()

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(f"{UPLOAD_DIR}/thumbnails", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/files", exist_ok=True)

router = APIRouter(prefix="/products", tags=["Products"])


def make_slug(title: str) -> str:
    """Convert title to URL-safe slug."""
    slug = title.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_-]+', '-', slug)
    slug = re.sub(r'^-+|-+$', '', slug)
    return slug


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
    query = db.query(models.Product).filter(models.Product.is_active == True)

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
    product = db.query(models.Product).filter(
        models.Product.slug == slug,
        models.Product.is_active == True
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


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


# 🚀 NAYA LOGIC YAHAN HAI: SMART FALLBACK FILE UPLOAD
@router.post("/{product_id}/upload-file")
async def upload_product_file(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Upload the downloadable file for a product."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()
    product.file_name = file.filename

    # Try Cloudflare R2 Upload first
    if upload_file_to_r2 and os.getenv('R2_ACCESS_KEY_ID'):
        try:
            r2_path = upload_file_to_r2(
                file_content=content,
                original_filename=file.filename,
                folder="files",
                content_type=file.content_type
            )
            product.file_url = r2_path
            db.commit()
            return {"message": "File uploaded successfully to Cloudflare R2", "file_name": file.filename}
        except Exception as e:
            print(f"R2 Upload failed, falling back to local storage: {e}")
            # Fallback to local storage niche continue hoga

    # Fallback: Local Storage (Agar R2 fail ho ya set na ho)
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"{UPLOAD_DIR}/files/{unique_name}"

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    product.file_url = file_path
    db.commit()

    return {"message": "File uploaded successfully to Local Storage", "file_name": file.filename}


# 🚀 NAYA LOGIC YAHAN HAI: SMART FALLBACK THUMBNAIL UPLOAD
@router.post("/{product_id}/upload-thumbnail")
async def upload_thumbnail(
    product_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: models.User = Depends(get_current_admin)
):
    """Admin: Upload a thumbnail image for a product."""
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    content = await file.read()

    # Try Cloudflare R2 Upload first
    if upload_file_to_r2 and os.getenv('R2_ACCESS_KEY_ID'):
        try:
            thumbnail_url = upload_file_to_r2(
                file_content=content,
                original_filename=file.filename,
                folder="thumbnails",
                content_type=file.content_type
            )
            product.thumbnail_url = thumbnail_url
            db.commit()
            return {"thumbnail_url": product.thumbnail_url, "source": "R2"}
        except Exception as e:
            print(f"R2 Thumbnail Upload failed, falling back to local: {e}")

    # Fallback: Local Storage (Agar R2 fail ho ya set na ho)
    ext = os.path.splitext(file.filename)[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = f"{UPLOAD_DIR}/thumbnails/{unique_name}"

    async with aiofiles.open(file_path, 'wb') as f:
        await f.write(content)

    product.thumbnail_url = f"/uploads/thumbnails/{unique_name}"
    db.commit()

    return {"thumbnail_url": product.thumbnail_url, "source": "Local"}