#!/usr/bin/env python3

import aiohttp.web
import argparse
import asyncio
import httpx
import json
import os
import secrets
import time
import types

OAUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"
ACTIVITIES_URL = "https://www.strava.com/api/v3/activities"

creds = types.SimpleNamespace(client_id=None, client_secret=None)
creds_file = None

activities = {}
activities_file = None
activities_done = None

server_state = None
server_port = None


def save_credentials():
    with open(creds_file, "w") as f:
        json.dump(
            {"client_id": creds.client_id,
             "client_secret": creds.client_secret,
             "access_token": getattr(creds, "access_token", None),
             "refresh_token": getattr(creds, "refresh_token", None),
             "expires_at": getattr(creds, "expires_at", None)}, f, indent=4)


def save_activities():
    with open(activities_file, "w") as f:
        json.dump(activities, f, indent=4)


def latlng_to_map_link(latlng, label="View on map"):
    """
    latlng: [lat, lng] as returned by Strava (e.g. [39.7392, -104.9903])
    label: link text for the HTML anchor
    """
    if not latlng or len(latlng) != 2:
        return "..."

    lat, lng = latlng
    # Google Maps link; you could swap this for OpenStreetMap if you prefer
    url = f"https://www.google.com/maps?q={lat},{lng}"
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'


async def activities_fetch():

    global activities
    global activities_done

    activities_done = False

    print("Start fetching activities...")

    timeout = httpx.Timeout(30.0, read=60.0) # long read timeout required, esp. for old activities

    per_page = 200 # Strava API max, minimizes requests
    page = 0

    async with httpx.AsyncClient(timeout=timeout) as client:

        while True:

            page += 1 # Strava API starts with page 1

            response = await client.get(
                ATHLETE_URL + "/activities",
                params={"per_page": per_page, "page": page},
                headers={"Authorization": f"Bearer {creds.access_token}"})

            if response.status_code == httpx.codes.ok:

                items = response.json()

                if page == 1 and max(activities.keys()) == items[0]["id"]:
                    print("Cached activities appear up to date.")
                    activities_done = True
                    break

                if not items:
                    print("Done fetching activities.")
                    activities_done = True
                    save_activities()
                    break

                print(f"Page {page} fetched with {len(items)}.")

                for item in items:

                    if item["id"] in activities:

                        activity = activities.get(item["id"])

                        if any(activity.get(k) != v for k, v in item.items()):
                            print(f"Updated activity found: {item['id']}")
                            activity.update(item)

                    else:
                        print(f"New activity found: {item['id']}")
                        activities[item["id"]] = item

            else:
                print(f"Fetch status_code: {response.status_code}, text: {response.text}")
                break


def do_oauth():

    global server_state

    server_state = secrets.token_hex(16)

    return aiohttp.web.Response(
        status=200,
        content_type="text/html",
        text="<html><a href=\"{}"
            "?client_id={}&response_type=code"
            "&redirect_uri=http://localhost:{}/oauth"
            "&approval_prompt=force"
            "&scope=activity:read_all,activity:write"
            "&state={}"
            "\">Click here to authenticate with Strava</a></html>".format(
                OAUTH_URL,
                creds.client_id,
                server_port,
                server_state))


def do_oauth_swap(error, code, state):

    global creds
    global server_state

    if error or not code:

        print(f"OAuth error: {error}, code: {code}")

        return aiohttp.web.Response(
            status=400,
            content_type="text/html",
            text="<html>OAuth failed. See log.</html>")

    # Check the state variable and discard to ensure it isn't reused

    if server_state != state:

        print(f"OAuth error server_state: {server_state}, state: {state}")

        return aiohttp.web.Response(
            status=400,
            content_type="text/html",
            text="<html>OAuth failed. State doesn't match. See log.</html>")

    server_state = None

    # Perform the token swap, redirect if it succeeds

    response = httpx.post(
        TOKEN_URL,
        data={"client_id": creds.client_id,
              "client_secret": creds.client_secret,
              "code": code,
              "grant_type": "authorization_code"})

    if response.status_code == httpx.codes.ok:
        creds.access_token  = response.json()["access_token"]
        creds.refresh_token = response.json()["refresh_token"]
        creds.expires_at    = response.json()["expires_at"]
        save_credentials()

        raise aiohttp.web.HTTPFound("/")

    else:

        print(f"OAuth swap status_code: {response.status_code}")

        return aiohttp.web.Response(
            status=400,
            content_type="text/html",
            text="<html>Oauth swap failed. See log.</html>")


def do_token_refresh():

    global creds

    response = httpx.post(
        TOKEN_URL,
        data={"client_id": creds.client_id,
              "client_secret": creds.client_secret,
              "refresh_token": creds.refresh_token,
              "grant_type": "refresh_token"})

    if response.status_code == httpx.codes.ok:
        creds.access_token  = response.json()["access_token"]
        creds.refresh_token = response.json()["refresh_token"]
        creds.expires_at    = response.json()["expires_at"]
        save_credentials()

    else:
        creds.access_token = None

        print(f"OAuth refresh status_code: {response.status_code}")


async def main_handler(request):

    path = request.path
    params = request.rel_url.query

    code  = params.get("code")
    state = params.get("state")
    error = params.get("error")

    if path == "/oauth":
        return do_oauth_swap(error, code, state)

    if path.startswith("/favicon.ico"):
        return aiohttp.web.Response(status=204)

    if not creds.access_token:
        return do_oauth()

    if not creds.expires_at or time.time() > creds.expires_at:
        print("Refreshing access token…")
        do_token_refresh()

    if not creds.access_token:
        return aiohttp.web.Response(
            status=400,
            content_type="text/html",
            text="<html>OAuth token refresh failed. See log.</html>")

    if activities_done is None:
        asyncio.create_task(activities_fetch())

    resp = aiohttp.web.StreamResponse(
        status=200,
        reason='OK',
        headers={'Content-Type': 'text/html'}
    )

    await resp.prepare(request)
    await resp.write(b"<html><body>")

    if activities_done:
        await resp.write("<p>Up to date</p>".encode("utf-8"))
    else:
        await resp.write("<p>Updating...</p>".encode("utf-8"))

    for a in activities.values():
        await resp.write(f"""
        <p><a href=\"https://www.strava.com/activities/{a['id']}\">{a['start_date']}</a>
        : {a['name']}
        , {a['sport_type']}
        , {a['distance']}m
        , {a['elapsed_time']}s
        {", Commute" if a.get('commute', False) else ", ..."}
        {", Private" if a['private'] else ", ..."}
        , {latlng_to_map_link(a.get("start_latlng", None), "Start")}
        , {latlng_to_map_link(a.get("end_latlng", None), "End")}
        </p>\n""".encode())

    await resp.write(b"</body></html>")
    await resp.write_eof()

    return resp


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="kom-kleaner")
    parser.add_argument("--credentials_file", required=True, help="path to credentials file")
    parser.add_argument("--activities_file", required=True, help="path to activities file")
    parser.add_argument("--port", type=int, default=8000, help="port to listen on")
    args = parser.parse_args()

    server_port = args.port
    creds_file = args.credentials_file
    activities_file = args.activities_file

    # Load credentials

    if not os.path.exists(creds_file):
        save_credentials()
    else:
        with open(creds_file, "r") as f:
            try:
                creds = types.SimpleNamespace(**json.load(f))

            except json.decoder.JSONDecodeError:
                raise RuntimeError("Credentials file is corrupt")

    if not creds.client_id:
        raise RuntimeError("Need a client ID")
    if not creds.client_secret:
        raise RuntimeError("Need a client secret")
    if not hasattr(creds, "access_token"):
        creds.access_token = None

    # Load activities file

    if not os.path.exists(activities_file):
        save_activities()
    else:
        with open(activities_file, "r") as f:
            try:
                activities = json.load(f)

            except json.decoder.JSONDecodeError:
                raise RuntimeError("Activities file is corrupt")

        # normalize the keys back to integers for use with Strava API

        activities = {int(k): v for k, v in activities.items()}

    # Start web interface

    app = aiohttp.web.Application()
    app.router.add_route("*", "/{tail:.*}", main_handler)

    aiohttp.web.run_app(app, port=server_port)
