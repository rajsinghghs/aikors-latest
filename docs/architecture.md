# Architecture

AIkors is a FastAPI store for digital study material. The browser UI is server-rendered Jinja templates plus a small amount of JavaScript. Data lives in Postgres (or any database pointed at by `DATABASE_URL`).

## Request flow

1. Pages such as `/`, `/product-page`, `/login`, and `/dashboard` return HTML from `templates/`.
2. The page scripts call JSON routes under `/api`.
3. `js/utils.js` keeps the session in `localStorage` (`cv_token`, `cv_user`) and sends `Authorization: Bearer`.
4. Checkout creates a Razorpay order, the browser opens Razorpay, then `/api/payments/verify` marks the order paid.
5. Download hits `/api/orders/download/{product_id}`. The handler checks a paid order (admins are allowed through) and either redirects to a short-lived R2 link or streams a local file.

## Main pieces

| Area | Files | Role |
| --- | --- | --- |
| App entry | `main.py` | FastAPI app, page routes, static mounts, table create, admin seed |
| Data | `models.py`, `database.py`, `schemas.py` | Users, products, orders, payments, reviews, preview screenshots |
| Auth | `routes/auth.py`, `auth/` | Email signup, login, Google redirect, password reset mail |
| Catalog | `routes/products.py` | Public list and detail, reviews, admin create, thumbnail, file, and screenshot upload |
| Orders | `routes/orders.py`, `routes/payments.py` | Razorpay create and verify, buyer download |
| Admin UI | `templates/admin_*.html`, `routes/admin.py` | Users, products, orders, payments |
| Files | `utils/r2_storage.py` | Cloudflare R2 upload and private download URLs |
| Policies | `policies.py`, `templates/policy.html` | Privacy, terms, refund, data safety |

## What is public

- Product title, price, description, category, tags, thumbnail, and preview screenshots.
- Reviews (name, stars, comment, verified-purchase flag).
- Sample layout images in `previews/` when a product has no uploaded screenshots yet.

The paid file URL is not part of the public product response. Only `file_name` is returned on the detail payload.

## Reviews

`reviews` has one row per user per product. Posting again updates that row. A review is marked verified when that user has a paid order containing the product. New tables are created on startup by `Base.metadata.create_all`.

## Screenshots

`product_screenshots` stores public preview images. Admins add them from the product editor. R2 uploads of type `screenshot` go in the `previews` folder and use the public R2 domain, same idea as thumbnails. Local fallback is `/uploads/previews/`.

## Hosting checklist

When the public domain changes:

- Set `BASE_URL` in `.env`. Google’s callback is `{BASE_URL}/api/auth/google/callback`.
- Update that redirect URL in Google Cloud Console.
- Add the site origin on the Cloudflare R2 bucket CORS rules.
- Set `SUPPORT_EMAIL` if the footer and policy pages should show a contact address.
