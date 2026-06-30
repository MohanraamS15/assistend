import requests

URL = "https://www.ucc-bsnl.co.in/header_link_doc/"

response = requests.get(URL)

response.raise_for_status()

with open("latest_headers.pdf", "wb") as f:
    f.write(response.content)

print("✅ PDF downloaded successfully.")

