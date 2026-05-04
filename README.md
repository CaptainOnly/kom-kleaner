# Setup

## Create an app at https://www.strava.com/settings/api 
Make the app URL localhost
App will have client ID and secret

## Create a credentials file with the id/secret
It should contain: {"client_id": "...", "client_secret": "..."}

## Start the app
python3 main.py --credentials_file ~/.ssh/strava

## Visit the URL printed
http://localhost:8000/
