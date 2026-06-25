# Self-hosting Cap (captcha)

Globalify uses [Cap](https://trycap.dev) — a self-hosted, reCAPTCHA-compatible
captcha — on the login and claim-profile forms. The integration is
**env-gated**: when the `_CAP_*` variables below are absent (dev / CI / test),
captcha verification is skipped entirely and everything works without a Cap
server. Once configured it **fails closed** (a missing/invalid token is
rejected).

## Quick-start: Cap standalone

Run the Cap standalone server (it needs a Redis/Valkey cache). See the
[standalone guide](https://trycap.dev/guide/standalone/). It is configured with:

| Var         | Purpose                                                     |
|-------------|-------------------------------------------------------------|
| `ADMIN_KEY` | Dashboard login (use 32+ chars)                             |
| `REDIS_URL` | Cache backend, e.g. `redis://valkey:6379`                   |

Once it's up, open the dashboard (authenticated with `ADMIN_KEY`) and create a
site. The dashboard gives you a **site key** and a **secret key** — these are
what the app uses below (they are *not* the same as `ADMIN_KEY`).

## Environment variables (the app)

Set these in your `.env` / deployment secrets. **All three are required** to
enable captcha — the site key is carried in the URL path, so it can't be
omitted.

| Variable             | Value                                                                            |
|----------------------|----------------------------------------------------------------------------------|
| `_CAP_API_ENDPOINT`  | Base URL of your Cap instance, **no site key**, e.g. `https://cap.globalify.org` |
| `_CAP_SITE_KEY`      | Site key from the Cap dashboard (appears in the widget + verify URL)             |
| `_CAP_SECRET`        | Secret key from the dashboard — server-side only, keep private                   |

```env
_CAP_API_ENDPOINT=https://cap.globalify.org
_CAP_SITE_KEY=your-site-key
_CAP_SECRET=your-secret-key
```

## How it works (current Cap protocol)

Cap addresses each site by its **site key in the URL path**:

1. The browser loads the widget from the CDN:
   `https://cdn.jsdelivr.net/npm/cap-widget@<version>` (pinned in the templates).
2. The `<cap-widget>` points at `data-cap-api-endpoint="{_CAP_API_ENDPOINT}/{_CAP_SITE_KEY}/"`
   (trailing slash) and solves a challenge there.
3. On submit the widget injects a hidden `cap-token` field.
4. The server calls `POST {_CAP_API_ENDPOINT}/{_CAP_SITE_KEY}/siteverify` with
   `{"secret": _CAP_SECRET, "response": <cap-token>}`.
5. If `success` is `false` (or the call errors), the request is rejected.

The per-site base URL is derived once, in `Settings.cap_site_endpoint`
(`config.py`); both the templates and `utils/cap.py` use it, so the site key is
never hard-coded in two places.

> **Upgrading the widget:** the CDN version is pinned in
> `templates/auth/login.html` and `templates/claiming/{email,manual}.html`.
> Bump all three together.

## Dev / CI behaviour

When any of `_CAP_API_ENDPOINT`, `_CAP_SITE_KEY`, or `_CAP_SECRET` is absent,
`verify_captcha` returns `True` immediately — no widget is rendered and no
network call is made. The test suite passes without a Cap server.
