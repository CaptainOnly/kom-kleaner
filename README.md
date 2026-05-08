## KOM KLEANER v2 but REAL'r

KOM Kleaner KV2 is a small local web app for browsing your Strava activities. It starts an HTTP server on your machine, walks you through Strava OAuth, stores the returned tokens in a local credentials JSON file, and renders paginated activity links in the browser.

The app uses Python 3.8+ and only the standard library.

## Setup

1. Create a Strava app at https://www.strava.com/settings/api.
2. Set the Strava app authorization callback domain to `localhost`.
   <img width="512" height="551" alt="image" src="https://github.com/user-attachments/assets/e18cfc3b-7f50-49f5-8e9c-1d1b653be89a" />
3. Create a credentials file:
```json
{
  "client_id": "your-client-id",
  "client_secret": "your-client-secret"
}
```

Keep that file outside the repository or use a local ignored filename such as `strava_credentials.json`.

## Run

```bash
python main.py --credentials-file strava_credentials.json
```

Then open http://127.0.0.1:8000/. The app will show a Strava authorization link if it does not already have an access token.

By default, the app binds to `127.0.0.1`, uses port `8000`, and requests `activity:read,activity:read_all` because private activities require the broader read scope. You can override those values:

```bash
python main.py --credentials-file strava_credentials.json --port 8080 --scope activity:read
```

If you change the port, make sure your Strava app can redirect to `http://localhost:<port>/oauth`.

## Development Checks

```bash
python -m py_compile main.py
python -m unittest
```
