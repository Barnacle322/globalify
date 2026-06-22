# Self-hosting Cap (captcha)

Globalify uses [Cap](https://github.com/nicholasgasior/cap) — a self-hosted,
reCAPTCHA-compatible captcha — on the login and claim-profile forms.  The
integration is **env-gated**: when the `_CAP_*` variables below are absent
(dev / CI / test), captcha verification is skipped entirely and everything
works without a Cap server.

## Quick-start: Docker Compose

Add a `cap` service to your `docker-compose.yml`:

```yaml
services:
  cap:
    image: ghcr.io/nicholasgasior/cap-standalone:latest   # or your own build
    ports:
      - "3001:3001"
    environment:
      CAP_SECRET: "your-cap-secret-here"
      CAP_SITE_KEY: "your-cap-site-key-here"
    restart: unless-stopped
```

After `docker compose up -d cap`, the Cap API is available at
`http://localhost:3001`.

## Environment variables

Set these in your `.env` (or deployment secrets):

| Variable             | Description                                                        |
|----------------------|--------------------------------------------------------------------|
| `_CAP_API_ENDPOINT`  | Base URL of your Cap server, e.g. `https://cap.yourapp.com`        |
| `_CAP_SITE_KEY`      | Site key configured in Cap (shown to the browser widget)           |
| `_CAP_SECRET`        | Server-side secret used in `siteverify` calls — keep this private  |

### Example `.env` snippet

```env
_CAP_API_ENDPOINT=https://cap.yourapp.com
_CAP_SITE_KEY=your-cap-site-key-here
_CAP_SECRET=your-cap-secret-here
```

## How it works

1. The browser loads `{_CAP_API_ENDPOINT}/cap.js` and renders the
   `<cap-widget>` on the login / claim forms.
2. On form submit the widget injects a hidden `cap-token` value.
3. The server calls `POST {_CAP_API_ENDPOINT}/siteverify` with
   `{"secret": ..., "response": cap-token}` (reCAPTCHA-compatible).
4. If `success` is `false` (or the call fails), the request is rejected with
   an error message and no action is taken.

## Dev / CI behaviour

When any of `_CAP_API_ENDPOINT` or `_CAP_SECRET` is absent, `verify_captcha`
returns `True` immediately — no widget is rendered and no network call is made.
The full test suite passes without a Cap server.
