# API notes

Base path is `/api`. Send `Authorization: Bearer <token>` for account, checkout, download, review writes, and every admin route.

## Public catalog

- `GET /products` — active products. Each item includes `avg_rating` and `review_count`.
- `GET /products/{slug}` — detail, including `file_name` and `screenshots`. Does not include `file_url`.
- `GET /products/{slug}/reviews` — `{ average, count, breakdown, purchased, my_review_id, reviews }`. `breakdown` is counts for stars `"1"` through `"5"`. `purchased` and `my_review_id` are set only when a valid token is sent.

Review objects contain `id`, `user_id`, `user_name`, `rating`, `comment`, `verified_purchase`, `created_at`.

## Signed-in buyer

- `POST /products/{slug}/reviews` with `{ "rating": 1-5, "comment": "" }` creates or updates that user’s single review. `comment` is optional.
- `DELETE /products/{slug}/reviews/mine` removes it.
- `POST /payments/create-order` with `{ "product_ids": [1] }` starts Razorpay checkout.
- `POST /payments/verify` confirms the signature and marks the order paid.
- `GET /orders` lists the current user’s orders.
- `GET /orders/download/{product_id}` streams the file or redirects to a temporary R2 URL. Requires a paid order.

## Admin

- `POST /products` creates a product and returns it, including the generated `slug`.
- `PUT /products/{id}` updates catalog fields.
- `DELETE /products/{id}` hides the product (`is_active = false`).
- `POST /products/{id}/get-upload-url` returns a direct R2 upload for `type` of `thumbnail`, `screenshot`, or a paid `file`.
- `POST /products/{id}/confirm-upload` saves that URL. `screenshot` adds a row instead of replacing the thumbnail.
- `POST /products/{id}/upload-thumbnail`, `upload-file`, and `upload-screenshot` are the local or server-side R2 fallbacks.
- `DELETE /products/{id}/screenshots/{screenshot_id}` removes a preview.
- `/admin/...` covers dashboard stats, users, orders, and the admin product list. The product list includes `screenshots` and does not return the private file URL.
