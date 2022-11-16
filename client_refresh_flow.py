import httpx

class RefreshFlow(httpx.Auth):
    def __init__(self, tokens, refresh_url):
        self.tokens = tokens
        self.refresh_url = refresh_url

    def auth_flow(self, request, attempt=0):
        request.headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
        response = yield request
        if response.status_code == 401:
            # The access token has expired.
            # Insert a request to get a new pair of tokens.
            token_request = httpx.Request(
                "POST",
                self.refresh_url,
                json={"refresh_token": self.tokens["refresh_token"]},
            )
            token_response = yield token_request
            if token_response.status_code == 401:
                raise Exception("Failed to refresh. Log in again.")
            token_response.read()
            new_tokens = token_response.json()
            self.tokens.update(new_tokens)

            # Retry the original request, using the new access token.
            request.headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
            yield request

if __name__ == "__main__":
    import time

    BASE_URL = "http://localhost:8000"
    client = httpx.Client(base_url=BASE_URL)
    tokens = client.post("/login", auth=("dallan", "password")).json()
    client.auth = RefreshFlow(tokens, f"{BASE_URL}/refresh")
    while True:
        print(client.get("/data"))
        time.sleep(2)
