# AIkors

When you change hosting, update the Google redirect URL in Google Cloud Console, add the new origin on Cloudflare R2 CORS, and change `BASE_URL` in `.env`.

AIkors sells digital study notes, e-books, and similar files. Buyers browse a catalog, pay with Razorpay, and download from their dashboard.

## Docs

- [Setup](docs/setup.md)
- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Privacy policy](docs/legal/privacy-policy.md)
- [Terms and conditions](docs/legal/terms-and-conditions.md)
- [Refund policy](docs/legal/refund-policy.md)
- [Data safety](docs/legal/data-safety.md)

The same policies are on the site at `/privacy`, `/terms`, `/refund`, and `/data-safety`.

```bash
uvicorn main:app --reload --port 8000
```
