"""
main.py - FastAPI application entry point
Run with: uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
import os
from dotenv import load_dotenv

# Load env before imports that depend on it
load_dotenv()

from database import engine, Base, ensure_schema
import models  # noqa: F401
from routes import auth, products, payments, orders, admin

# ─── App Init ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="AIkors API",
    description="Premium digital course & asset selling platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ─── CORS ────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Static Files & Templates ────────────────────────────────────────────────
app.mount("/js", StaticFiles(directory="js"), name="js")
app.mount("/css", StaticFiles(directory="css"), name="css")

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

# Public images only — paid files stay private
app.mount("/uploads/thumbnails", StaticFiles(directory=f"{UPLOAD_DIR}/thumbnails"), name="thumbnails")
app.mount("/uploads/previews", StaticFiles(directory=f"{UPLOAD_DIR}/previews"), name="previews")
app.mount("/previews", StaticFiles(directory="previews"), name="sample-previews")

templates = Jinja2Templates(directory="templates")
templates.env.globals["support_email"] = os.getenv("SUPPORT_EMAIL", "").strip()

# ─── Custom 404 Handler ──────────────────────────────────────────────────────
@app.exception_handler(404)
async def custom_404_handler(
    request: Request,
    exc: Exception,
):
    # API calls returning 404 should return JSON
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"},
        )

    # UI calls return 404 template
    return templates.TemplateResponse(
        request=request,
        name="404.html",
        status_code=404,
    )

# ─── Frontend Routes (Pages) ─────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@app.get("/login", response_class=HTMLResponse)
async def serve_login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
    )


@app.get("/signup", response_class=HTMLResponse)
async def serve_signup(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="signup.html",
    )


@app.get("/forgot-password", response_class=HTMLResponse)
async def serve_forgot_password(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="forgot_password.html",
    )


@app.get("/reset-password", response_class=HTMLResponse)
async def serve_reset_password(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="reset_password.html",
    )

@app.get("/dashboard", response_class=HTMLResponse)
async def serve_user_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
    )


@app.get("/product-page", response_class=HTMLResponse)
async def serve_product(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="product.html",
    )


def _policy_page(request: Request, key: str):
    from policies import POLICIES
    page = POLICIES[key]
    return templates.TemplateResponse(
        request=request,
        name="policy.html",
        context={
            "page_title": page["title"],
            "updated": page["updated"],
            "body": page["body"],
        },
    )


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    return _policy_page(request, "privacy")


@app.get("/terms", response_class=HTMLResponse)
async def terms_page(request: Request):
    return _policy_page(request, "terms")


@app.get("/refund", response_class=HTMLResponse)
async def refund_policy(request: Request):
    return _policy_page(request, "refund")


@app.get("/data-safety", response_class=HTMLResponse)
async def data_safety(request: Request):
    return _policy_page(request, "data_safety")


# ─── FAANG-Level Admin Routing (Separate Pages) ──────────────────────────────

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_dashboard.html",
    )


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_users.html",
    )


@app.get("/admin/users/{user_id}", response_class=HTMLResponse)
async def admin_user_detail(
    request: Request,
    user_id: int,
):
    return templates.TemplateResponse(
        request=request,
        name="admin_user_detail.html",
        context={
            "user_id": user_id,
        },
    )


@app.get("/admin/products", response_class=HTMLResponse)
async def admin_products(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_products.html",
    )


@app.get("/admin/reviews", response_class=HTMLResponse)
async def admin_reviews(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_reviews.html",
    )


@app.get("/admin/orders", response_class=HTMLResponse)
async def admin_orders(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_orders.html",
    )


@app.get("/admin/payments", response_class=HTMLResponse)
async def admin_payments(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="admin_payments.html",
    )

# ─── API Routes ──────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(payments.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# ─── DB Init ─────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    """Create tables and seed admin user on first run."""
    Base.metadata.create_all(bind=engine)
    ensure_schema()
    await seed_admin()

async def seed_admin():
    """Create default admin user if not exists."""
    from database import SessionLocal
    from auth.password import hash_password

    db = SessionLocal()
    try:
        admin_email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        admin_password = os.getenv("ADMIN_PASSWORD", "AdminPass123!")

        existing = db.query(models.User).filter(
            models.User.email == admin_email
        ).first()

        if not existing:
            admin = models.User(
                name="Admin",
                email=admin_email,
                hashed_password=hash_password(admin_password),
                role=models.UserRole.admin
            )
            db.add(admin)
            db.commit()
            print(f"✅ Admin created: {admin_email}")
        else:
            print(f"ℹ️  Admin already exists: {admin_email}")
    finally:
        db.close()

# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "AIkors API"}

# ─── Global Error Handler ────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )