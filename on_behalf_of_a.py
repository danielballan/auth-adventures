import base64
import time
from datetime import datetime, timedelta

import httpx
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from jwt_sketch import create_jwt, read_jwt


# Simulated external services
def check_password(username, password):
    return password == "password"  # Placeholder


def unauthorized(message="..."):
    return JSONResponse({"error": message}, status_code=401)


def create_token(payload, lifetime):
    payload["exp"] = int((datetime.now() + timedelta(seconds=lifetime)).timestamp())
    return create_jwt(payload)


def authenticate(request):
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    payload = read_jwt(param)
    if payload is None or payload["type"] != "access":
        return None
    return payload


# Service A: front end enddpoint with on-behalf-of logic.
# Client of Service B in outer closure of service.
service_b_client = httpx.Client(base_url="http://localhost:8001")


# Login endpoint with scopes
async def login(request):
    service_b_client.auth = None  # Reset OBO auth on login
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "basic":
        return unauthorized()
    username, _, password = base64.b64decode(param).decode().partition(":")
    if not check_password(username, password):
        print(f"Bad credentials: {username!r} {password!r}")
        return unauthorized()
    access_token = create_token(
        {"sub": username, "type": "access", "scope": "read:principal"}, lifetime=10
    )
    refresh_token = create_token(
        {"sub": username, "type": "refresh", "scope": "read:principal"},
        lifetime=14 * 24 * 60 * 60,
    )
    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token})


# Refresh endpoint with scopes
async def refresh(request):
    data = await request.json()
    payload = read_jwt(data["refresh_token"])
    if payload is None or payload["type"] != "refresh":
        return unauthorized("Invalid refresh token")
    username = payload["sub"]
    access_token = create_token(
        {"sub": username, "type": "access", "scope": "read:principal"}, lifetime=10
    )
    refresh_token = create_token(
        {"sub": username, "type": "refresh", "scope": "read:principal"},
        lifetime=14 * 24 * 60 * 60,
    )
    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token})


class OBORefreshFlow(httpx.Auth):
    def __init__(self, tokens, refresh_url):
        self.tokens = tokens
        self.refresh_url = refresh_url

    def auth_flow(self, request):
        # Attach the current access token to the request
        request.headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
        response = yield request

        if response.status_code == 401:
            # The access token has expired. Refresh the tokens.
            token_request = httpx.Request(
                "POST",
                self.refresh_url,
                json={"refresh_token": self.tokens["refresh_token"]},
            )
            token_response = yield token_request

            if token_response.status_code == 401:
                raise Exception("Failed to refresh on behalf of. Log in again.")

            # Fully read the token response content asynchronously
            token_response.read()
            new_tokens = token_response.json()
            self.tokens.update(new_tokens)

            # Retry the original request with the new access token
            request.headers["Authorization"] = f"Bearer {self.tokens['access_token']}"
            yield request


def on_behalf_of_auth(request):
    authorization_header = request.headers.get("Authorization", "")

    # Call Service B's on-behalf-of endpoint to get tokens for the principal
    response = service_b_client.post(
        "/on-behalf-of",
        headers={"Authorization": authorization_header},
        json={"principal": "goofy"},
    )
    if response.status_code != 200:
        return unauthorized(f"Failed to fetch OBO tokens: {response.status_code}")

    # Extract tokens from Service B's response
    tokens = response.json()

    # Set up OBO auth flow for Service B
    service_b_client.auth = OBORefreshFlow(
        tokens, f"{service_b_client.base_url}/refresh"
    )


async def print_service(request):
    # Authenticate the client token
    client_payload = authenticate(request)
    if not client_payload:
        return unauthorized("Invalid or missing access token")
    client_username = client_payload["sub"]

    if service_b_client.auth is None:
        on_behalf_of_auth(request)

    # Use the OBO tokens to call Service B's /data endpoint
    counter = 0
    while True:
        if counter > 10:
            break
        counter += 1
        response = service_b_client.get("/data")
        if response.status_code != 200:
            return unauthorized(
                f"Failed to fetch data from Service B: {response.status_code}"
            )

        # Parse and log the response from Service B
        data_response = response.json()
        print(f"Service A User: {client_username}")
        print(f"Service B response: {data_response}")
        time.sleep(2)
    return JSONResponse({"status": "done"})


routes = [
    Route("/login", login, methods=["POST"]),
    Route("/refresh", refresh, methods=["POST"]),
    Route("/data", print_service, methods=["GET"]),
]
app = Starlette(routes=routes)
