import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
import secrets

import httpx
from jose import jwk, jwt
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
# jwt_sketch is a local module in this directory with a toy JWT implementation.
from jwt_sketch import create_jwt, read_jwt
from http_basic_into_oauth2 import authenticate, refresh
from tiled.client import from_uri

BASE_URL = "http://localhost:8000"
WEB_APP_URL = "http://localhost:8001/"

SIMPLE_OIDC_BASE_URL = "http://localhost:9000"
TENNANT_ID = os.environ["TENNANT_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
TILED_SCOPE = os.environ["TILED_SCOPE"]  # e.g. api://<app-b-client-id>/access_as_user
APP_SCOPE = os.environ["APP_SCOPE"]  # e.g. api://<app-b-client-id>/access_as_user
TILED_URL = "https://tiled-demo.nsls2.bnl.gov"
AUTH_ENDPOINT = f"https://login.microsoftonline.com/{TENNANT_ID}/oauth2/v2.0/authorize"
TOKEN_ENDPOINT = f"https://login.microsoftonline.com/{TENNANT_ID}/oauth2/v2.0/token"

# When the simple-oidc-provider starts, it generates fresh random certs.
# Downlaod them here. In a real application, this would be configured separately.
KEYS = httpx.get(f"https://login.microsoftonline.com/{TENNANT_ID}/discovery/v2.0/keys").json()["keys"]
import os
for key in KEYS:
    key["alg"] = "RS256"
authorization_uri = httpx.URL(
    AUTH_ENDPOINT,
    params={
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": f"openid {APP_SCOPE}",
        "redirect_uri": f"{BASE_URL}/device_code_callback",
    }
)
print(f"Authorization URI: {authorization_uri}")

async def code(request):
    code = request.query_params["code"]
    username, entra_access_token = exchange_code_for_username(code, WEB_APP_URL)
    access_token = create_token(
        {"sub": username, "type": "access", "entra_token": entra_access_token},
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

def exchange_code_for_username(code, redirect_uri):
    auth_value = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    response = httpx.post(
        url=TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
        headers={"Authorization": f"Basic {auth_value}"},
    )
    response.raise_for_status()
    response_body =  response.json()
    id_token = response_body["id_token"]
    access_token = response_body["access_token"]

    # Verify that response is from the trusted server.
    unverified = jwt.get_unverified_header(id_token)
    kid = unverified["kid"]
    for candidate_key in KEYS:
        if candidate_key["kid"] == kid:
            key = jwk.construct(candidate_key)
            break
    else:
        raise Exception(f"Could not find kid {kid} among {[key['kid'] for key in KEYS]}")
    verified_body = jwt.decode(
        id_token, key, access_token=access_token, audience=CLIENT_ID
    )
    username = verified_body["sub"]
    return username, access_token

def exchange_token_obo(entra_access_token):
    """Exchange an App A Entra token for one scoped to Tiled via OBO."""
    response = httpx.post(
        url=TOKEN_ENDPOINT,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "assertion": entra_access_token,
            "scope": TILED_SCOPE,
            "requested_token_use": "on_behalf_of",
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]

@dataclass
class PendingSession:
    user_code: str
    device_code: str
    deadline: datetime
    username: str = None
    entra_access_token: str = None

PENDING_SESSIONS = []  # placeholder for a proper database

def unauthorized(message="..."):
    return JSONResponse({"error": message}, status_code=401)

def create_token(payload, lifetime):
    payload["exp"] = int((datetime.now() + timedelta(seconds=lifetime)).timestamp())
    return create_jwt(payload)

async def authorize(request):
    user_code = secrets.token_hex(4).upper()  # 8-digit code
    device_code = secrets.token_hex(32)
    deadline = datetime.now() + timedelta(minutes=15)
    pending_session = PendingSession(
        user_code=user_code, device_code=device_code, deadline=deadline
    )
    PENDING_SESSIONS.append(pending_session)
    print(f"Created {pending_session}")
    verification_uri = f"{BASE_URL}/token"
    return JSONResponse(
        {
            "authorization_uri": str(authorization_uri),
            "verification_uri": str(verification_uri),
            "interval": 2,  # seconds
            "device_code": device_code,
            "expires_in": 15 * 60,  # seconds
            "user_code": user_code,
        }
    )

async def device_code_callback(request):
    code = request.query_params["code"]
    return HTMLResponse(f"""
<html>
    <body>
        <form action="{BASE_URL}/device_code_form" method="post">
            <label for="user_code">Enter code</label>
            <input type="text" id="user_code" name="user_code" />
            <input type="hidden" id="code" name="code" value="{code}" />
            <input type="submit" value="Enter" />
        </form>
    </body>
</html>""")

async def handle_device_code_form(request):
    # The identity provider calls this route via a redirect the user's browser.
    # Here in the server, contact the identity provider with the provided code,
    # and exchange it for information about the user.
    form_data = await request.form()
    redirect_uri = f"{BASE_URL}/device_code_callback"
    username, entra_access_token = exchange_code_for_username(form_data["code"], redirect_uri)
    
    # Update the pending session with the username from the identity provider.
    for pending_session in PENDING_SESSIONS:
        if pending_session.user_code == form_data["user_code"]:
            pending_session.username = username
            pending_session.entra_access_token = entra_access_token
            print(f"Verified {pending_session}")
            status_code = 200
            message = "And there was much rejoicing!"
            break
    else:
        status_code = 401
        message = "Fail!"
    return HTMLResponse(f"<html><body>{message}</body></html>", status_code=status_code)

async def token(request):
    # Is there a pending session for this device code? Has it been verified yet?
    form_data = await request.form()
    device_code = form_data["device_code"]
    for pending_session in PENDING_SESSIONS:
        if pending_session.deadline < datetime.now():
            PENDING_SESSIONS.remove(pending_session)
            print(f"Expired {pending_session}")
            continue
        if pending_session.device_code == form_data["device_code"]:
            if pending_session.username is None:
                return unauthorized("pending")
            # The pending session for this device code is verified!
            # Return some tokens below.
            PENDING_SESSIONS.remove(pending_session)
            print(f"Used {pending_session}")
            break
    else:
        return unauthorized("unrecognized device code -- maybe expired")
    access_token = create_token(
        {"sub": pending_session.username, "type": "access", "entra_token": pending_session.entra_access_token},
        # lifetime=10 * 60  # 10 minutes
        lifetime=10  # 10 seconds
    )
    refresh_token = create_token(
        {"sub": pending_session.username, "type": "refresh"},
        lifetime=14 * 24 * 60 * 60  # 2 weeks
    )
    return JSONResponse(
        {"refresh_token": refresh_token, "access_token": access_token}
    )

async def data(request):
    # Validate App A's access token and extract the embedded Entra token.
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return unauthorized("missing token")
    app_a_token = auth_header.removeprefix("Bearer ")
    try:
        payload = read_jwt(app_a_token)
    except Exception:
        return unauthorized("invalid token")
    if payload.get("type") != "access":
        return unauthorized("wrong token type")
    if payload.get("exp", 0) < datetime.now().timestamp():
        return unauthorized("token expired")

    entra_token = payload.get("entra_token")
    if not entra_token:
        return unauthorized("no entra token in payload")

    # OBO exchange: get a token scoped to Tiled.
    try:
        tiled_token = exchange_token_obo(entra_token)
    except httpx.HTTPStatusError as e:
        return JSONResponse({"error": "OBO exchange failed", "detail": e.response.text}, status_code=502)

    # Build Tiled client and inject the OBO token.
    client = from_uri(TILED_URL)
    client.context.http_client.auth.tokens.update({
        "access_token": tiled_token,
        "refresh_token": None,
    })

    return JSONResponse({"context": repr(client.context), "keys": list(client.keys().head())})

routes = [
    Route("/data", data, methods=["GET"]),
    Route("/authorize", authorize, methods=["POST"]),
    Route("/code", code, methods=["GET"]),
    Route("/device_code_callback", device_code_callback, methods=["GET"]),
    Route("/device_code_form", handle_device_code_form, methods=["POST"]),
    Route("/token", token, methods=["POST"]),
    Route("/refresh", refresh, methods=["POST"])
]
app = Starlette(routes=routes)
