import base64
from datetime import datetime, timedelta

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
# jwt_sketch is a local module in this directory with a toy JWT implementation.
from jwt_sketch import create_jwt, read_jwt

def check_password(username, password):
    # Interact with some external system like PAM or LDAP....
    return password == "password"  # placeholder

def unauthorized(message="..."):
    return JSONResponse({"error": message}, status_code=401)

def create_token(payload, lifetime):
    payload["exp"] = int((datetime.now() + timedelta(seconds=lifetime)).timestamp())
    return create_jwt(payload)

async def login(request):
    # Verify Authorization header is "Basic {base64-encoded username:password}"
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "basic":
        return unauthorized()
    username, _, password = base64.b64decode(param).decode().partition(":")
    if not check_password(username, password):
        print(f"Bad credentials: {username!r} {password!r}")
        return unauthorized()
    access_token = create_token(
        {"sub": username, "type": "access"},
        # lifetime=10 * 60  # 10 minutes
        lifetime=10  # 10 seconds
    )
    refresh_token = create_token(
        {"sub": username, "type": "refresh"},
        lifetime=14 * 24 * 60 * 60  # 2 weeks
    )
    return JSONResponse(
        {"refresh_token": refresh_token, "access_token": access_token}
    )

def authenticate(request):
    # Verify Authorization header is "Bearer {access_token}"
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "bearer":
        return None
    payload = read_jwt(param)
    if (payload is None) or (payload["type"] != "access"):
        return None
    return payload["sub"]

def data(request):
    username = authenticate(request)
    if not username:
        return JSONResponse({"error": "..."}, status_code=401)
    return JSONResponse({"data": [1, 2, 3], "who_am_i": username})

async def refresh(request):
    # Expect body {"refresh_token": ...}
    data = await request.json()
    payload = read_jwt(data["refresh_token"])
    if (payload is None) or (payload["type"] != "refresh"):
        return unauthorized(payload)
    username = payload["sub"]
    access_token = create_token(
        {"sub": username, "type": "access"},
        # lifetime=10 * 60  # 10 minutes
        lifetime=10  # 10 seconds
    )
    refresh_token = create_token(
        {"sub": username, "type": "refresh"},
        lifetime=14 * 24 * 60 * 60  # 2 weeks
    )
    return JSONResponse(
        {"refresh_token": refresh_token, "access_token": access_token}
    )

routes = [
    Route("/data", data, methods=["GET"]),
    Route("/login", login, methods=["POST"]),
    Route("/refresh", refresh, methods=["POST"])
]
app = Starlette(routes=routes)
