# Setup

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`. Interactive API docs are at `/api/docs`.

`DATABASE_URL` is required. On startup the app creates any missing tables and inserts the admin user from `ADMIN_EMAIL` and `ADMIN_PASSWORD` if that email does not exist yet.

## Environment

| Variable | Used for |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy database |
| `SECRET_KEY` | Login tokens and password-reset tokens |
| `BASE_URL` | Password-reset links and the Google redirect |
| `ADMIN_EMAIL`, `ADMIN_PASSWORD` | First admin account |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Checkout |
| `SMTP_SERVER`, `SMTP_PORT`, `SMTP_EMAIL`, `SMTP_PASSWORD` | Password reset email |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google sign-in |
| `R2_*` | Optional Cloudflare storage for thumbnails, previews, and paid files |
| `SUPPORT_EMAIL` | Address shown in the footer |
| `UPLOAD_DIR` | Local folder for thumbnails, previews, and paid files when R2 is not used |

Paid files under `uploads/files` are not mounted as public static files. Thumbnails and preview images are.

## Pages

| URL | Page |
| --- | --- |
| `/` | Catalog |
| `/product-page?slug=...` | Product, previews, reviews, checkout |
| `/login`, `/signup` | Account |
| `/dashboard` | Purchased downloads |
| `/privacy`, `/terms`, `/refund`, `/data-safety` | Policies |
| `/admin` | Admin home |

## Admin content previews

1. Create the product and save it.
2. In the same editor, upload one or more preview images (PNG, JPG, or WebP).
3. Those images replace the sample pages on the product screen.
4. Upload the private PDF or ZIP separately. Buyers only receive that file after payment.
