from datetime import datetime
import time
import webbrowser

import httpx

from client_refresh_flow import RefreshFlow

def login(client):
    info = client.post("/authorize").json()
    print(f"""You have {info['expires_in']} seconds to enter the code 

    {info['user_code']}

after authorizing at the URL:

    {info['authorization_uri']}
""")
    webbrowser.open(info["authorization_uri"])  # Try to open a web browser.
    deadline = datetime.now().timestamp() + info["expires_in"]

    # Poll the /token endpoing waiting for this pending session to be verified.
    print("Waiting...", end="", flush=True)
    while datetime.now().timestamp() < deadline:
        response = client.post("/token", data={"device_code": info["device_code"]})
        print(".", end="", flush=True)
        if response.status_code == 200:
            print("\nLogged in!")
            break
        time.sleep(info["interval"])
    tokens = response.json()
    client.auth = RefreshFlow(tokens, f"{client.base_url}/refresh")
    return client

if __name__ == "__main__":
    import time

    client = httpx.Client(base_url="http://localhost:8000")
    login(client)
    print(client.get("/data"))
    print(client.get("/data").json())
