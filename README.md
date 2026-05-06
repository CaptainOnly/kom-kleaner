Project Overview: KOM KLEANER but REAL'r

This Hons style project is a Python-based utility that interacts with the Strava API to fetch and display athlete activities - which you can already do in Strava. It features a custom http.server implementation to handle OAuth authentication flows and provide a simple web interface for browsing through your activity history.

Features
OAuth2 Integration: Handles authorization with Strava to securely access athlete data.

Activity Feed: Fetches a list of recent activities, including names, dates, and direct links to Strava.

Pagination: Includes a built-in "Next Page" feature to navigate through large activity histories.

Local Web Server: Uses a custom BaseHTTPRequestHandler to render data directly in your browser.

Requirements
Python 3.6+

Requests Library: To handle API calls.

Strava API Credentials: You must register an application at the Strava Developers portal to get your Client ID and Client Secret.

Installation
Clone the repository:

Bash
git clone https://github.com/yourusername/KOM-KLEANER-REAL.git

cd KOM-KLEANER-REAL

Install dependencies:

Bash
pip install requests
Configuration
Before running the script, ensure you have set up your environment variables or updated the main.py file with your Strava credentials:

CLIENT_ID: Your Strava application ID.

CLIENT_SECRET: Your Strava application secret.

ATHLETE_URL: Typically [https://www.strava.com/api/v3/athlete](https://www.strava.com/api/v3/athlete).

Usage
Start the server:

Bash
python main.py
Authenticate:
Open your browser and navigate to the local server address (usually http://localhost:8000). You will be redirected to Strava to authorize the application.

Browse Activities:
Once authorized, the app will display a list of your activities. You can click on the activity names to view them on Strava or use the "Next Page..." link at the bottom to see older entries.

Technical Details
KomHandler Class
A custom request handler that:

Intercepts the /activities endpoint.

Calculates the current page from the URL parameters.

Performs a GET request to the Strava API using the stored access_token.

Parses the JSON response and generates a dynamic HTML page.

API Integration
The app requests 200 activities per page (max allowed by Strava) to minimize API round-trips while maintaining a smooth user experience.
