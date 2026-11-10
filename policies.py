"""Customer-facing policy copy for AIkors.

The store sells digital study material (notes, e-books, PDFs, and similar files)
through Razorpay. Accounts use email and password, with optional Google sign-in.
Paid files stay private. Preview images and thumbnails can be public.
"""

UPDATED = "10 November 2026"

CONTACT = (
    "Use the support email in the site footer when one is published. "
    "Otherwise write from the email on your AIkors account and include your order number. "
    "The store operator can set that public address with the SUPPORT_EMAIL environment variable."
)


POLICIES = {
    "privacy": {
        "title": "Privacy Policy",
        "updated": UPDATED,
        "body": f"""
<p>This policy explains what AIkors collects when you browse the store, create an account, pay for digital study material, or leave a review. It matches how this website actually works.</p>
<h2>Who we are</h2>
<p>AIkors is the operator of this website. We sell digital educational files such as notes, e-books, assignments, and exam material. Prices are charged in Indian rupees through Razorpay.</p>
<h2>Information we collect</h2>
<ul>
  <li><strong>Account.</strong> Name, email address, and a hashed password. If you sign in with Google, we receive the profile details Google shares for that login (such as name and email) and store an account on AIkors.</li>
  <li><strong>Orders.</strong> Products you buy, the price at purchase, order status, and the time of the order.</li>
  <li><strong>Payments.</strong> Razorpay order id, payment id, signature, amount, currency, status, and payment method (for example UPI, card, or netbanking). We do not store your full card number, CVV, or UPI PIN. Razorpay processes the payment.</li>
  <li><strong>Delivery.</strong> The private file attached to a product, and the fact that your paid order unlocked it. Download links for paid files are temporary.</li>
  <li><strong>Reviews.</strong> The star rating and comment you submit, shown with your account name.</li>
  <li><strong>On your device.</strong> The site stores your login token and basic profile in the browser (<code>cv_token</code> and <code>cv_user</code>) so you stay signed in. That is local storage, not an advertising cookie.</li>
</ul>
<h2>How we use it</h2>
<ul>
  <li>Create and secure your account, including password reset email links that expire after 15 minutes.</li>
  <li>Take payment, record the order, and unlock the file you bought.</li>
  <li>Show product reviews and verified-purchase labels.</li>
  <li>Respond to refund and support requests.</li>
  <li>Keep the store reliable and investigate failed or duplicate payments.</li>
</ul>
<h2>Who else processes data</h2>
<ul>
  <li><strong>Razorpay</strong> handles checkout.</li>
  <li><strong>Google</strong> handles sign-in only if you choose Google login.</li>
  <li><strong>Cloudflare R2</strong> stores thumbnails, preview screenshots, and paid files when that storage is configured. Thumbnails and preview screenshots may be public. Paid files are not listed publicly.</li>
  <li><strong>Email provider</strong> (the SMTP settings on the server, often Gmail) sends password-reset mail.</li>
</ul>
<p>We do not sell personal information.</p>
<h2>How long we keep it</h2>
<p>Account and order records stay while your account is active and as needed for payment records, refunds, and disputes. You can ask us to delete your account. We may keep a minimal order and payment record where the law or a payment dispute requires it.</p>
<h2>Your choices</h2>
<p>You can update your name from the account tools the store provides, sign out on this browser, and ask us to correct or delete your account. Deleting an account removes your ability to download purchases tied to it.</p>
<p>{CONTACT}</p>
<h2>Security</h2>
<p>Passwords are stored as hashes. Paid downloads are allowed only after we confirm a paid order for that account (admins can also open files to support the store). Use the site over HTTPS in production.</p>
<h2>Children</h2>
<p>AIkors is not directed at children under 13. Do not create an account if you are under 13.</p>
""",
    },
    "terms": {
        "title": "Terms and Conditions",
        "updated": UPDATED,
        "body": f"""
<p>These terms cover use of the AIkors website and the digital study material sold here. Creating an account or paying for a product means you accept them.</p>
<h2>The product</h2>
<p>Products are digital files (for example PDF or ZIP notes, e-books, assignments, and exam material). After a successful payment, the file is unlocked on your dashboard for download. Access is tied to your account. Unless a product page says otherwise, this is a personal licence to study from the file, not a transfer of copyright.</p>
<h2>Your account</h2>
<p>You must give a real name and an email address you can open. You are responsible for activity under your login, including Google sign-in if you connect it. We may suspend an account that is used to attack the site, share paid files publicly, or abuse checkout.</p>
<h2>Acceptable use</h2>
<ul>
  <li>Do not copy, resell, upload, or share paid files with people who have not bought them.</li>
  <li>Do not try to download a file you have not purchased.</li>
  <li>Do not post reviews that are unrelated to the product, or that include someone else's private information.</li>
</ul>
<h2>Prices and payment</h2>
<p>Prices are shown in INR. Checkout runs on Razorpay. A product is delivered when the payment is verified and the order status is paid. An unpaid or failed order does not include the file.</p>
<h2>Reviews</h2>
<p>Signed-in users can leave one review per product and can edit or delete it later. If that account has a paid order for the product, the review is marked as a verified purchase. We may remove a review that breaks these terms.</p>
<h2>No exam guarantee</h2>
<p>Notes and practice material are study aids. AIkors does not promise marks, admission, or a particular exam result.</p>
<h2>Changes and availability</h2>
<p>We may update a file, change a price, or hide a product. If you already have a paid order, you keep access to the file that was attached for that purchase while your account remains active and the order stays paid. Refunds are covered in the Refund Policy.</p>
<h2>Liability</h2>
<p>The site and files are provided as study material. To the extent the law allows, we are not liable for indirect losses such as lost study time or exam outcomes. Nothing here limits liability that cannot legally be limited.</p>
<h2>Law</h2>
<p>These terms follow the applicable laws of India.</p>
<p>{CONTACT}</p>
""",
    },
    "refund": {
        "title": "Refund Policy",
        "updated": UPDATED,
        "body": f"""
<p>AIkors sells digital files that can be downloaded right after payment. Because the content is delivered immediately, refunds are limited to failed delivery and billing mistakes.</p>
<h2>When you can ask for a refund</h2>
<p>Write to us within 7 days of payment if any of these happened:</p>
<ul>
  <li>Money was taken but the order never became paid, and you still cannot download the file.</li>
  <li>The file opens as corrupt, empty, or is a different product from the one you paid for.</li>
  <li>You were charged twice for the same product.</li>
</ul>
<h2>When a refund is not available</h2>
<ul>
  <li>You already downloaded a working file.</li>
  <li>You changed your mind, picked the wrong subject, or no longer need the notes.</li>
  <li>The request is about expected marks or how useful you found the material after reading a working file.</li>
</ul>
<h2>How to request it</h2>
<p>Contact us with the email on your account, the product name, the order time, and the Razorpay payment id if you have it. {CONTACT}</p>
<h2>How a refund is sent</h2>
<p>Approved refunds go back through Razorpay to the original payment method. Banks and UPI apps decide how long that takes. When an order is marked refunded, download access for that order is removed.</p>
""",
    },
    "data_safety": {
        "title": "Data Safety",
        "updated": UPDATED,
        "body": f"""
<p>This page is a short data-safety summary for anyone reviewing AIkors, including payment or store review. It describes the website, not a separate mobile app binary.</p>
<h2>Data the store collects</h2>
<ul>
  <li><strong>Name and email</strong> — account creation, receipts, and password reset.</li>
  <li><strong>Password</strong> — stored only as a hash. Google sign-in does not give us your Google password.</li>
  <li><strong>Purchase history</strong> — which products you paid for, so we can unlock downloads.</li>
  <li><strong>Payment references</strong> — Razorpay ids, amount, currency, status, and method. Card numbers, CVV, and UPI PIN stay with Razorpay.</li>
  <li><strong>Reviews</strong> — rating and comment, shown with your name.</li>
  <li><strong>Files an admin uploads</strong> — the product thumbnail, preview screenshots, and the private download.</li>
</ul>
<h2>Data the store does not collect</h2>
<ul>
  <li>Precise location, contacts, SMS, or your photo library.</li>
  <li>Advertising identifiers or a cross-site tracking profile.</li>
  <li>Full payment card data.</li>
</ul>
<h2>Why it is collected</h2>
<p>Account access, checkout, delivering the file you bought, showing reviews, and handling refunds. We do not sell this data.</p>
<h2>Sharing</h2>
<ul>
  <li>Razorpay, to complete the payment.</li>
  <li>Google, only if you choose Google sign-in.</li>
  <li>Cloudflare R2, to store images and paid files when configured. Preview screenshots are meant to be seen before purchase. Paid files are served only to the buyer (or an admin) through a checked download.</li>
  <li>The email service configured on the server, for password reset.</li>
</ul>
<h2>Security practices</h2>
<ul>
  <li>Passwords are hashed.</li>
  <li>The browser keeps the session token in local storage.</li>
  <li>Paid file links are not published on the product page. The API returns the file name, not the private file URL.</li>
  <li>Production traffic should use HTTPS.</li>
</ul>
<h2>Deletion</h2>
<p>You can ask for your account to be deleted. Orders that are refunded lose download access. {CONTACT}</p>
<h2>Audience</h2>
<p>The store is for students and adult buyers. It is not directed at children under 13.</p>
""",
    },
}
