from datetime import datetime, timedelta

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

from jwt_sketch import create_jwt, read_jwt

PRINCIPAL_ACCESS = {"dallan": ["donald", "mickey", "goofy"], "pmaffetto": ["minnie"]}


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


# On behalf of endpoint
async def on_behalf_of(request):
    # First ensure the user is allowed to access the service
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "bearer":  # No basic login authentication
        return unauthorized(
            f"Failed to authenticate on behalf of user.\n scheme={scheme}\n Authorization_header={authorization_header}"
        )
    payload = read_jwt(param)
    if (payload is None) or (payload["type"] != "access"):
        return None
    username = payload["sub"]
    scope = payload["scope"]

    if scope != "read:principal" and username not in PRINCIPAL_ACCESS:
        return unauthorized("Insufficient permissions")

    # Next ensure the user can access the principal
    # This could more appropriately be done in a separate service that has knowledge of users and principals
    data = await request.json()
    principal = data.get("principal")
    if principal not in PRINCIPAL_ACCESS[username]:
        return unauthorized("Insufficient permissions, principal not found")

    # Finally, mint the new tokens
    access_token = create_token(
        {"sub": principal, "type": "access", "scope": "read:data"}, lifetime=10
    )
    refresh_token = create_token(
        {"sub": principal, "type": "refresh", "scope": "read:data"},
        lifetime=14 * 24 * 60 * 60,
    )
    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token})


# Refresh endpoint
async def refresh(request):
    data = await request.json()
    payload = read_jwt(data["refresh_token"])
    if payload is None or payload["type"] != "refresh":
        return unauthorized("Invalid refresh token")
    username = payload["sub"]
    scope = payload["scope"]
    access_token = create_token(
        {"sub": username, "type": "access", "scope": scope}, lifetime=10
    )
    refresh_token = create_token(
        {"sub": username, "type": "refresh", "scope": scope}, lifetime=14 * 24 * 60 * 60
    )
    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token})


async def data(request):
    payload = authenticate(request)
    if not payload:
        return unauthorized("Failed to authenticate")
    return JSONResponse({"data": [1, 2, 3], "who_am_i": payload["sub"]})


routes = [
    Route("/data", data, methods=["GET"]),
    Route("/on-behalf-of", on_behalf_of, methods=["POST"]),
    Route("/refresh", refresh, methods=["POST"]),
]
app = Starlette(routes=routes)
