#!/usr/bin/env python3

import argparse
import http.server
import json
import requests
import secrets
import sys
import time
import urllib.parse

OAUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"


class KomHandler(http.server.BaseHTTPRequestHandler):

    def do_oauth_swap(self, error, code, state):

        if error or not code:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html>OAuth failed. See log.</html>".encode())
            raise RuntimeError(f"Oath failed error: {error}, {code}")

        # Check the state variable and discard so we don't reuse state
        # for later OAuth requests

        if self.server.state != state:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html>OAuth state doesn't match</html>".encode())
            raise RuntimeError("Oath state doesn't match")

        self.server.state = None

        # Perform the token swap, redirect if it succeeds

        response = requests.post(
            TOKEN_URL,
            data={"client_id": self.server.client_id,
                  "client_secret": self.server.client_secret,
                  "code": code,
                  "grant_type": "authorization_code"})

        if response.status_code == requests.codes.ok:
            self.server.access_token  = response.json()["access_token"]
            self.server.refresh_token = response.json()["refresh_token"]
            self.server.expires_at    = response.json()["expires_at"]
            self.server.save_credentials()

            self.send_response(302)
            self.send_header("Location", "/activities")
            self.end_headers()

        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html>Oauth swap failed. See log.</html>")
            raise RuntimeError(f"Oath failed: {response.status_code}, {response.text}")

    def do_oauth(self):

        # Update server state if necessary

        if not self.server.state:

            self.server.state = secrets.token_hex(16)

            print(f"OAuth State: {self.server.state}")

        # Provide the OAuth link

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            "<html><a href=\"{}"
            "?client_id={}&response_type=code"
            "&redirect_uri=http://localhost:{}/oauth"
            "&approval_prompt=force"
            "&scope=activity:read_all,activity:write"
            "&state={}"
            "\">Click here</a></html>"
            .format(
                OAUTH_URL,
                self.server.client_id,
                self.server.server_port,
                self.server.state).encode())

    def do_token_refresh(self):

        print("Refreshing access token…")

        response = requests.post(
            TOKEN_URL,
            data={"client_id": self.server.client_id,
                  "client_secret": self.server.client_secret,
                  "refresh_token": self.server.refresh_token,
                  "grant_type": "refresh_token"})

        if response.status_code == requests.codes.ok:
            self.server.access_token  = response.json()["access_token"]
            self.server.refresh_token = response.json()["refresh_token"]
            self.server.expires_at    = response.json()["expires_at"]
            self.server.save_credentials()

        else:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("<html>Token refresh failed. See log.</html>")
            raise RuntimeError(f"token refresh failed: {response.status_code}, {response.text}")

    def do_activites(self, page):

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        response = requests.get(
            ATHLETE_URL + "/activities",
            params={"per_page": 20, "page": page},
            headers={"Authorization": "Bearer {}".format(
                self.server.access_token)})

        if response.status_code == requests.codes.ok:

            self.wfile.write(f"<html>\n<h1>Page: {page}</h1>\n".encode())

            for a in response.json():
                self.wfile.write(f"<p><a href=\"https://www.strava.com/activities/{a['id']}\">".encode())
                self.wfile.write(f"{a['start_date']}</a>".encode())
                self.wfile.write(f": {a['name']}, {a['sport_type']}".encode())
                self.wfile.write(f", {a['distance']}m, {a['elapsed_time']}s, {a['gear_id']}".encode())
                self.wfile.write("</a></p>\n".encode())

            self.wfile.write(
                "<p><a href=\"/activities?page={}\">Next Page...</a></p>\n</html>\n".format(
                    int(page) + 1).encode())

        else:
            self.wfile.write("<html>Activity fetch failed. See log.</html>")
            raise RuntimeError(f"Activity fetch failed: {response.status_code}, {response.text}")

    def do_GET(self):

        parsed = urllib.parse.urlparse(self.path)

        params = urllib.parse.parse_qs(parsed.query)
        code  = params.get("code",  [None])[0]
        state = params.get("state",  [None])[0]
        error = params.get("error", [None])[0]
        page  = params.get("page",  [1])[0]

        if parsed.path == "/oauth":

            return self.do_oauth_swap(error, code, state)

        if self.path.startswith("/favicon.ico"):

            self.send_response(204) # No Content
            self.send_header("Content-Length", "0")
            self.end_headers()

            return None

        if not self.server.access_token:

            return self.do_oauth()

        if not self.server.expires_at or time.time() > self.server.expires_at:

            self.do_token_refresh()

        if parsed.path == "/activities":

            return self.do_activites(page)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(f"<html><a href=\"/activities\">Maybe you want this?</a></html>".encode())

class KomServer(http.server.HTTPServer):

    def __init__(self, addr, credentials_file):

        super().__init__(addr, KomHandler)

        self.credentials_file = credentials_file

        self.load_credentials()

        if not self.client_id:
            raise RuntimeError("Need a client ID")
        if not self.client_secret:
            raise RuntimeError("Need a client secret")

        self.state = None

    def load_credentials(self):
        with open(self.credentials_file, "r") as f:
            try:
                creds = json.load(f)

            except json.decoder.JSONDecodeError:
                raise RuntimeError("Credentials file is corrupt")

            self.client_id     = creds.get("client_id", None)
            self.client_secret = creds.get("client_secret", None)
            self.access_token  = creds.get("access_token", None)
            self.refresh_token = creds.get("refresh_token", None)
            self.expires_at    = creds.get("expires_at", None)

    def save_credentials(self):
        with open(self.credentials_file, "w") as f:
            json.dump(
                {"client_id": self.client_id,
                 "client_secret": self.client_secret,
                 "access_token": self.access_token,
                 "refresh_token": self.refresh_token,
                 "expires_at": self.expires_at}, f)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="kom-kleaner")
    parser.add_argument("--credentials_file", required=True, help="path to credentials file")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on")
    args = parser.parse_args()

    server = KomServer(("127.0.0.1", args.port), args.credentials_file)
    print(f"Listening on http://localhost:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

