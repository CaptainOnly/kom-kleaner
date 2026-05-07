import argparse
import html
import http.server
import json
import os
import secrets
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ACTIVITIES_URL = "https://www.strava.com/api/v3/athlete/activities"
AUTHORIZE_URL = "https://www.strava.com/oauth/authorize"
DEFAULT_SCOPE = "activity:read,activity:read_all"
DEFAULT_TIMEOUT_SECONDS = 15
PER_PAGE = 200


class CredentialsError(RuntimeError):
    pass


class ApiResponse:
    def __init__(self, status_code, body, data=None):
        self.status_code = status_code
        self.body = body
        self.data = data


def parse_page(value):
    try:
        page = int(value)
    except (TypeError, ValueError):
        return 1

    return max(page, 1)


def load_json_file(path):
    path = Path(path).expanduser()

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError as exc:
        raise CredentialsError(
            "Credentials file not found. Create one with client_id and client_secret."
        ) from exc
    except json.JSONDecodeError as exc:
        raise CredentialsError("Credentials file is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise CredentialsError("Credentials file must contain a JSON object.")

    return data


def save_json_file(path, data):
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")

    try:
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.write("\n")

        try:
            os.chmod(temp_path, 0o600)
        except OSError:
            pass

        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def build_authorization_url(client_id, port, scope, state, redirect_host):
    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": f"http://{redirect_host}:{port}/oauth",
        "approval_prompt": "auto",
        "scope": scope,
        "state": state,
    }
    return AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)


def request_json(url, method="GET", fields=None, access_token=None, timeout=DEFAULT_TIMEOUT_SECONDS):
    headers = {"Accept": "application/json"}
    body = None

    if fields is not None:
        body = urllib.parse.urlencode(fields).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"

    request = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
            return ApiResponse(response.status, raw_body, parse_json_body(raw_body))
    except urllib.error.HTTPError as exc:
        raw_body = exc.read().decode("utf-8", errors="replace")
        return ApiResponse(exc.code, raw_body, parse_json_body(raw_body))
    except urllib.error.URLError as exc:
        return ApiResponse(0, str(exc.reason), None)


def parse_json_body(body):
    if not body:
        return None

    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def format_distance(meters):
    try:
        miles = float(meters) / 1609.344
    except (TypeError, ValueError):
        return ""

    return f"{miles:.2f} mi"


def format_duration(seconds):
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return ""

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours}h {minutes:02d}m"

    if minutes:
        return f"{minutes}m {seconds:02d}s"

    return f"{seconds}s"


def render_page(title, body):
    safe_title = html.escape(title)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light dark;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }}

    body {{
      margin: 0;
      padding: 2rem;
      background: Canvas;
      color: CanvasText;
    }}

    main {{
      max-width: 820px;
      margin: 0 auto;
    }}

    a {{
      color: LinkText;
    }}

    .activity {{
      border-block-end: 1px solid color-mix(in srgb, CanvasText 18%, transparent);
      padding: 1rem 0;
    }}

    .activity h2 {{
      font-size: 1.05rem;
      margin: 0 0 0.25rem;
    }}

    .meta {{
      color: color-mix(in srgb, CanvasText 72%, transparent);
      margin: 0;
    }}

    .actions {{
      display: flex;
      gap: 1rem;
      margin-top: 2rem;
    }}

    .error {{
      border-inline-start: 4px solid #c43;
      padding-inline-start: 1rem;
    }}
  </style>
</head>
<body>
  <main>
    {body}
  </main>
</body>
</html>
"""


def render_activities(activities, page):
    lines = [f"<h1>Activities: page {page}</h1>"]

    if not activities:
        lines.append("<p>No activities returned for this page.</p>")
    else:
        for activity in activities:
            activity_id = str(activity.get("id") or "").strip()
            name = html.escape(str(activity.get("name") or "Unnamed activity"))
            start_date = html.escape(
                str(activity.get("start_date_local") or activity.get("start_date") or "Unknown date")
            )
            sport_type = html.escape(
                str(activity.get("sport_type") or activity.get("type") or "Activity")
            )
            distance = html.escape(format_distance(activity.get("distance")))
            moving_time = html.escape(format_duration(activity.get("moving_time")))
            meta = " | ".join(value for value in [start_date, sport_type, distance, moving_time] if value)

            if activity_id:
                href = "https://www.strava.com/activities/" + urllib.parse.quote(activity_id)
                heading = f'<a href="{href}">{name}</a>'
            else:
                heading = name

            lines.append(
                '<section class="activity">'
                f"<h2>{heading}</h2>"
                f'<p class="meta">{meta}</p>'
                "</section>"
            )

    previous_link = ""
    if page > 1:
        previous_link = f'<a href="/activities?page={page - 1}">Previous page</a>'

    lines.append(
        '<nav class="actions">'
        f"{previous_link}"
        f'<a href="/activities?page={page + 1}">Next page</a>'
        "</nav>"
    )

    return render_page(f"Activities page {page}", "\n".join(lines))


def render_error(title, message, details=None):
    lines = [
        f'<div class="error"><h1>{html.escape(title)}</h1>',
        f"<p>{html.escape(message)}</p>",
    ]

    if details:
        lines.append(f"<pre>{html.escape(str(details))}</pre>")

    lines.append("</div>")
    return render_page(title, "\n".join(lines))


class KomHandler(http.server.BaseHTTPRequestHandler):
    server_version = "KomKleaner/2"

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/oauth":
            return self.handle_oauth(params)

        if parsed.path == "/activities":
            if not self.server.access_token:
                return self.show_oauth_link()
            return self.handle_activities(params.get("page", [1])[0])

        if parsed.path in ("", "/"):
            if self.server.access_token:
                return self.redirect("/activities")
            return self.show_oauth_link()

        if parsed.path == "/favicon.ico":
            return self.send_empty(404)

        return self.send_html(
            404,
            render_error("Not found", "Try /activities or restart the OAuth flow from /."),
        )

    def handle_oauth(self, params):
        error = params.get("error", [None])[0]
        code = params.get("code", [None])[0]
        state = params.get("state", [None])[0]

        if error:
            return self.send_html(400, render_error("OAuth error", error))

        if not code:
            return self.send_html(400, render_error("OAuth error", "Missing authorization code."))

        if not state or not secrets.compare_digest(state, self.server.oauth_state):
            return self.send_html(400, render_error("OAuth error", "Invalid OAuth state."))

        self.server.rotate_oauth_state()
        token_response = self.exchange_token(
            {
                "client_id": self.server.client_id,
                "client_secret": self.server.client_secret,
                "code": code,
                "grant_type": "authorization_code",
            }
        )

        if (
            token_response.status_code == 200
            and isinstance(token_response.data, dict)
            and token_response.data.get("access_token")
        ):
            self.server.update_tokens(token_response.data)
            return self.redirect("/activities")

        return self.send_html(
            400,
            render_error("OAuth failed", "Strava did not return an access token.", token_response.body),
        )

    def show_oauth_link(self):
        url = build_authorization_url(
            self.server.client_id,
            self.server.server_port,
            self.server.scope,
            self.server.oauth_state,
            self.server.redirect_host,
        )
        body = (
            "<h1>Connect Strava</h1>"
            "<p>KOM Kleaner needs a Strava authorization code before it can list activities.</p>"
            f'<p><a href="{html.escape(url, quote=True)}">Connect your Strava account</a></p>'
        )
        return self.send_html(200, render_page("Connect Strava", body))

    def handle_activities(self, page_value):
        page = parse_page(page_value)
        url = ACTIVITIES_URL + "?" + urllib.parse.urlencode({"per_page": PER_PAGE, "page": page})
        response = request_json(url, access_token=self.server.access_token, timeout=self.server.timeout)

        if response.status_code == 200 and isinstance(response.data, list):
            return self.send_html(200, render_activities(response.data, page))

        if response.status_code == 401 and self.server.refresh_token:
            if self.refresh_access_token():
                return self.redirect(f"/activities?page={page}")

        if response.status_code == 401:
            self.server.clear_tokens()
            return self.show_oauth_link()

        return self.send_html(
            502,
            render_error("Strava request failed", f"HTTP status: {response.status_code}", response.body),
        )

    def refresh_access_token(self):
        token_response = self.exchange_token(
            {
                "client_id": self.server.client_id,
                "client_secret": self.server.client_secret,
                "refresh_token": self.server.refresh_token,
                "grant_type": "refresh_token",
            }
        )

        if (
            token_response.status_code == 200
            and isinstance(token_response.data, dict)
            and token_response.data.get("access_token")
        ):
            self.server.update_tokens(token_response.data)
            return True

        return False

    def exchange_token(self, fields):
        return request_json(TOKEN_URL, method="POST", fields=fields, timeout=self.server.timeout)

    def redirect(self, location):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def send_empty(self, status):
        self.send_response(status)
        self.end_headers()

    def send_html(self, status, document):
        body = document.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), format % args))


class KomServer(http.server.HTTPServer):
    def __init__(self, addr, credentials_file, scope, redirect_host, timeout):
        super().__init__(addr, KomHandler)
        self.credentials_file = Path(credentials_file).expanduser()
        self.scope = scope
        self.redirect_host = redirect_host
        self.timeout = timeout
        self.oauth_state = ""

        self.load_credentials()
        self.rotate_oauth_state()

    def load_credentials(self):
        creds = load_json_file(self.credentials_file)
        self.client_id = str(creds.get("client_id") or "").strip()
        self.client_secret = str(creds.get("client_secret") or "").strip()
        self.access_token = creds.get("access_token")
        self.refresh_token = creds.get("refresh_token")

        if not self.client_id:
            raise CredentialsError("Credentials file is missing client_id.")
        if not self.client_secret:
            raise CredentialsError("Credentials file is missing client_secret.")

    def save_credentials(self):
        save_json_file(
            self.credentials_file,
            {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
            },
        )

    def update_tokens(self, token_data):
        access_token = token_data.get("access_token")
        if not access_token:
            raise CredentialsError("Token response is missing access_token.")

        self.access_token = access_token
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        self.save_credentials()

    def clear_tokens(self):
        self.access_token = None
        self.refresh_token = None
        self.save_credentials()

    def rotate_oauth_state(self):
        self.oauth_state = secrets.token_urlsafe(32)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="Local Strava activity viewer")
    parser.add_argument(
        "--credentials-file",
        "--credentials_file",
        required=True,
        help="Path to a JSON file containing client_id and client_secret.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on.")
    parser.add_argument(
        "--redirect-host",
        default="localhost",
        help="Host name used in the OAuth redirect URI registered with Strava.",
    )
    parser.add_argument(
        "--scope",
        default=DEFAULT_SCOPE,
        help="Comma-separated Strava OAuth scopes to request.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Timeout, in seconds, for Strava API requests.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        server = KomServer(
            (args.host, args.port),
            args.credentials_file,
            scope=args.scope,
            redirect_host=args.redirect_host,
            timeout=args.timeout,
        )
    except CredentialsError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print(f"Listening on http://{args.host}:{args.port}/")
    print(f"OAuth redirect URI: http://{args.redirect_host}:{args.port}/oauth")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
    
