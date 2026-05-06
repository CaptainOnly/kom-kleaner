#!/usr/bin/env python3

import argparse
import http.server
import json
import requests
import sys
import urllib.parse

TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"

class KomHandler(http.server.BaseHTTPRequestHandler):

    def handle_oauth(self, error, code):

        if error or not code:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"OAuth error: {error}".encode())
            return

        # Grab the auth code, perform the token swap, and redirect

        response = requests.post(
            TOKEN_URL,
            data={"client_id": self.server.client_id,
                  "client_secret": self.server.client_secret,
                  "code": code,
                  "grant_type": "authorization_code"})

        if response.status_code == requests.codes.ok:
            self.server.access_token  = response.json()["access_token"]
            self.server.refresh_token = response.json()["refresh_token"]
            self.server.save_credentials()

            self.send_response(302)
            self.send_header("Location", "/activities")
            self.end_headers()

        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(f"OAuth failed: {response.status_code}, {response.text}".encode())

    def do_oauth(self):

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write("<html><a href=\"https://www.strava.com/oauth/authorize?client_id={}&response_type=code&redirect_uri=http://localhost:{}/oauth&approval_prompt=force&scope=activity:read_all,activity:write\">Click here</a></html>".format(self.server.client_id, self.server.server_port).encode("utf-8"))

    def do_token_refresh(self, redirect_url):

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
            self.server.save_credentials()

            self.send_response(302)
            self.send_header("Location", redirect_url)
            self.end_headers()

        else:
            print("Refresh failed: {}, {}".format(response.status_code, response.json()))
            sys.exit(1)

    def handle_activites(self, page):

        response = requests.get(
            ATHLETE_URL + "/activities",
            params={"per_page": 200, "page": page},
            headers={"Authorization": "Bearer {}".format(
                self.server.access_token)})

        if response.status_code == requests.codes.ok:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<html>Got a page!</html>".encode("utf-8"))

        elif response.status_code == requests.codes.unauthorized:

            self.do_token_refresh(f"/activities?page={page}")

    def do_GET(self):

        parsed = urllib.parse.urlparse(self.path)

        print("Serving {}, with params {}".format(parsed.path, parsed.query))

        params = urllib.parse.parse_qs(parsed.query)
        code   = params.get("code",  [None])[0]
        error  = params.get("error", [None])[0]
        page   = params.get("page",  [1])[0]

        if parsed.path == "/oauth":

            return self.handle_oauth(error, code)

        if not self.server.access_token:

            return self.do_oauth()

        if parsed.path == "/activities":

            return self.handle_activites(page)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(f"<html><a href=\"/activities\">Maybe you want this?</a></html>".encode("utf-8"))

class KomServer(http.server.HTTPServer):

    def __init__(self, addr, credentials_file):

        super().__init__(addr, KomHandler)

        self.credentials_file = credentials_file

        self.load_credentials()

        if not self.client_id:
            raise RuntimeError("Need a client ID")
        if not self.client_secret:
            raise RuntimeError("Need a client secret")

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

    def save_credentials(self):
        with open(self.credentials_file, "w") as f:
            json.dump(
                {"client_id": self.client_id,
                 "client_secret": self.client_secret,
                 "access_token": self.access_token,
                 "refresh_token": self.refresh_token}, f)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="kom-kleaner")
    parser.add_argument("--credentials_file", required=True, help="path to credentials file")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on")
    args = parser.parse_args()

    server = KomServer(('', args.port), args.credentials_file)
    print(f"Listening on http://localhost:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()

