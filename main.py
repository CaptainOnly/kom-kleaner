# --- Request Section ---
# Consolidate params and use f-strings for cleaner headers
response = requests.get(
    f"{ATHLETE_URL}/activities",
    params={"per_page": 200, "page": page},
    headers={"Authorization": f"Bearer {self.server.access_token}"}
)

# --- Handler Section ---
if response.status_code == 200:
    self.send_response(200)
    self.send_header("Content-type", "text/html; charset=utf-8")
    self.end_headers()

    # Build the HTML body
    activities = response.json()
    
    html_lines = [
        "<html>",
        f"<h1>Page: {page}</h1>"
    ]

    for a in activities:
        # Use f-strings for readability and .get() for safety
        act_id = a.get("id")
        date = a.get("start_date")
        name = a.get("name")
        html_lines.append(
            f'<p><a href="https://www.strava.com/activities/{act_id}">{date}: {name}</a></p>'
        )

    next_page = int(page) + 1
    html_lines.append(f'<p><a href="/activities?page={next_page}">Next Page...</a></p>')
    html_lines.append("</html>")

    # Join and encode once
    self.wfile.write("\n".join(html_lines).encode("utf-8"))

elif response.status_code == requests.codes.unauthorized:
    # Handle unauthorized...