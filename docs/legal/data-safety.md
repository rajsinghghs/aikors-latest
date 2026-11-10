# Data Safety

Last updated: 10 November 2026

This is the same summary published at `/data-safety`. It describes this website for a store or payment review.

Collected:

- name and email
- password hash (Google password is never received)
- purchase history
- Razorpay payment references, not full card data
- reviews (rating, comment, account name)
- admin-uploaded thumbnails, preview screenshots, and the private product file

Not collected:

- precise location, contacts, or SMS
- advertising identifiers
- full card numbers, CVV, or UPI PIN

Shared with Razorpay (payments), Google (only if Google sign-in is used), Cloudflare R2 (files, when configured), and the SMTP provider (password reset).

Preview screenshots are public so buyers can see the content before paying. Paid files are not on the public product payload.

Users can request account deletion. The store is not directed at children under 13.
