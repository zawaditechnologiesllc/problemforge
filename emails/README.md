# Email setup: Resend + Supabase Auth

ProblemForge sends two kinds of email, both through **Resend**:

| Kind | Sent by | Examples | Configured where |
|---|---|---|---|
| Auth emails | Supabase Auth via **Resend SMTP** | signup confirmation, password reset, magic link, email change, invite | Supabase dashboard (templates in this folder) |
| Transactional | The backend via the **Resend API** | FTO report ready, support replies, new-support-message notices | `RESEND_API_KEY` + `EMAIL_FROM` env on Render |

## 1. Verify your domain in Resend (the anti-spam foundation)

1. [resend.com](https://resend.com) → **Domains → Add Domain** → add your
   sending domain (use a subdomain like `mail.yourdomain.com` or the apex).
2. Resend shows DNS records — add them all at your DNS provider:
   - **DKIM** (TXT records) — cryptographically signs your mail.
   - **SPF** (TXT, usually on the `send` subdomain Resend specifies) —
     authorizes Resend's servers to send for you.
   - **MX** for the bounce subdomain (Return-Path alignment).
3. Wait for the domain to show **Verified**. Do not send from an unverified
   domain — that is the #1 cause of spam-foldering.
4. Add a **DMARC** record yourself (Resend doesn't require it, inboxes love it):
   ```
   _dmarc.yourdomain.com  TXT  "v=DMARC1; p=quarantine; rua=mailto:dmarc@yourdomain.com; adkim=s; aspf=s"
   ```
   Start with `p=none` for a week if you want to observe before enforcing.

## 2. Point Supabase Auth at Resend SMTP

Supabase dashboard → **Project Settings → Auth → SMTP Settings**:

| Field | Value |
|---|---|
| Host | `smtp.resend.com` |
| Port | `465` (SSL) |
| Username | `resend` |
| Password | your Resend API key (`re_...`) |
| Sender email | e.g. `auth@yourdomain.com` (on the verified domain) |
| Sender name | `ProblemForge` |

Also raise the rate limit (Auth → Rate Limits → emails per hour) above the
default 30/h once you're on custom SMTP.

## 3. Install the templates

Supabase dashboard → **Authentication → Email Templates** — paste the HTML
body from each file and set the subject:

| Template | File | Suggested subject |
|---|---|---|
| Confirm signup | `confirm-signup.html` | Confirm your ProblemForge email |
| Reset password | `reset-password.html` | Reset your ProblemForge password |
| Magic link | `magic-link.html` | Your ProblemForge sign-in link |
| Change email address | `change-email.html` | Confirm your new email address |
| Invite user | `invite.html` | You're invited to ProblemForge |

The templates use Supabase's Go-template variables (`{{ .ConfirmationURL }}`,
`{{ .Email }}`, `{{ .NewEmail }}`) — paste them as-is. The confirmation URLs
route through the app's `/auth/callback`, which already handles success,
password-recovery redirects, and expired-link errors.

Also set **Authentication → URL Configuration**: Site URL = your production
domain, and make sure `https://your-domain/auth/callback` is in the redirect
allow-list (see DEPLOYMENT.md step 1).

## 4. Backend transactional email

Set on the Render web service:

```
RESEND_API_KEY=re_...
EMAIL_FROM=ProblemForge <notifications@yourdomain.com>   # verified domain!
EMAIL_REPLY_TO=support@yourdomain.com                    # optional
```

Leave them empty and the product still works — emails are best-effort by
design and never block a request.

## 5. Staying out of spam — checklist

- [ ] Resend domain shows **Verified** (DKIM + SPF green)
- [ ] DMARC record published; sender domains align with the From address
- [ ] Auth sender and `EMAIL_FROM` both use the verified domain (never gmail.com etc.)
- [ ] Send a signup + reset + FTO email to [mail-tester.com](https://www.mail-tester.com) — aim for 9+/10
- [ ] Every backend email includes a plain-text part (built-in) and no tracking pixels or shorteners (we use neither)
- [ ] Keep transactional and any future marketing sending on separate subdomains

Honest note: correct authentication + clean content gets transactional email
to the inbox in the overwhelming majority of cases, but no one can guarantee
inbox placement — mailbox providers score sender reputation over time. The
setup above is the full set of controls that are actually in your hands.
