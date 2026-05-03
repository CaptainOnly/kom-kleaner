#!/usr/bin/env python3

import datetime
import json
import requests
import sys

TOKEN_URL = "https://www.strava.com/api/v3/oauth/token"
ATHLETE_URL = "https://www.strava.com/api/v3/athlete"

if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage: kom-kleaner <CREDENTIAL_FILE>")
        sys.exit(1)

    with open(sys.argv[1], "r") as f:
        creds = json.load(f)

    client_id     = creds["client_id"]
    client_secret = creds["client_secret"]
    access_token  = creds["access_token"]
    refresh_token = creds["refresh_token"]

    # Test that the access token works, refresh if not

    response = requests.get(
        ATHLETE_URL,
        headers={"Authorization": f"Bearer {access_token}"})

    if response.status_code == requests.codes.ok:
        print("Access token is valid.")
    elif response.status_code == requests.codes.unauthorized:
        print("Refreshing access token…")

        response = requests.post(
            TOKEN_URL,
            data={"client_id": client_id,
                  "client_secret": client_secret,
                  "grant_type": "refresh_token",
                  "refresh_token": refresh_token})

        if response.status_code == requests.codes.ok:
            creds["access_token"] = response.json()["access_token"]
            creds["refresh_token"] = response.json()["refresh_token"]

            with open(sys.argv[1], "w") as f:
                json.dump(creds, f)

        else:
            print("Refresh failed: {}, {}".format(response.status_code, response.json()))

    else:
        print("Access test failed: {}, {}".format(response.status_code, response.json()))

    # Grab some activities

    page = 1
    while True:
        response = requests.get(
            ATHLETE_URL + "/activities",
            params={"per_page": 200, "page": page},
            headers={"Authorization": "Bearer {}".format(creds["access_token"])})

        if response.status_code == requests.codes.ok:
            for activity in response.json():
                print("{}: {}".format(
                    activity["start_date"],
                    activity["name"]))

        if response.status_code == requests.codes.unauthorized:
            print("Authorization errors: {}".format(response.json()['errors']))
            sys.exit(1)

        page += 1
