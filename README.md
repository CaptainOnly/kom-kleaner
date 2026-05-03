# Setup

## Create an app at https://www.strava.com/settings/api 
Make the app URL localhost
App will have client ID and secret

## Visit this OAuth authorization URL in your browser, login and approve as necessary:
https://www.strava.com/oauth/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://localhost&approval_prompt=force&scope=activity:read_all,activity:write

## Copy the authorization code from the redirect URL
http://localhost/?code=...
  
## Exchange the authorization code for access/refresh tokens
> curl -X POST https://www.strava.com/api/v3/oauth/token \
  -d client_id=CLIENT_ID \
  -d client_secret=CLIENT_SECRET \
  -d code=AUTHORIZATION_CODE \
  -d grant_type=authorization_code

{"token_type":"Bearer", ..., "refresh_token":"...", "access_token":"...", ...}

## Save the tokens in a private credentials file
{"client_id": "...", "client_secret": "...", "access_token": "...", "refresh_token": "..."}
