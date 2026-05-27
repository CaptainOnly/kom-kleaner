# Overview

A web-app for interacting with the Strava API. Mostly a vehcicle for a certain someone to learn Python.

# Setup

## Create an app at https://www.strava.com/settings/api 
Make the app URL localhost. App will have client ID and secret.

## Create a JSON format credentials file with the id/secret
It should contain: {"client_id": "...", "client_secret": "..."}

## Start the app
python main.py --credentials_file <credentials file path>

## Visit the URL printed
http://localhost:8000/

# FAQ

## Can I run this on a public server?

If you know to ask this question, you know the answer is no.
