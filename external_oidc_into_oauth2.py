import base64
from dataclasses import dataclass
from datetime import datetime, timedelta
import secrets

import httpx
from jose import jwk, jwt
from starlette.applications import Starlette
from starlette.responses import JSONResponse, HTMLResponse
from starlette.routing import Route
# jwt_sketch is a local module in this directory with a toy JWT implementation.
from jwt_sketch import create_jwt, read_jwt
from http_basic_into_oauth2 import authenticate, data, refresh

BASE_URL = "http://localhost:8000"

SIMPLE_OIDC_BASE_URL = "http://localhost:9000"
AUTH_ENDPOINT = f"{SIMPLE_OIDC_BASE_URL}/auth"
TOKEN_ENDPOINT = f"{SIMPLE_OIDC_BASE_URL}/token"
CLIENT_ID = "example_client_id"
CLIENT_SECRET = "example_client_secret"

# When the simple-oidc-provider starts, it generates fresh random certs.
# Downlaod them here. In a real application, this would be configured separately.
KEYS = httpx.get(f"{SIMPLE_OIDC_BASE_URL}/certs").json()["keys"]
for key in KEYS:
    key["alg"] = "RS256"
authorization_uri = httpx.URL(
    AUTH_ENDPOINT,
    params={
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": "openid",
        "redirect_uri": f"{BASE_URL}/device_code_callback",
    }
)

@dataclass
class PendingSession:
    user_code: str
    device_code: str
    deadline: datetime
    username: str = None

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
    auth_value = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    response = httpx.post(
        url=TOKEN_ENDPOINT,
        data={
            "grant_type": "authorization_code",
            "redirect_uri": f"{BASE_URL}/device_code_callback",
            "code": form_data["code"],
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
        raise Exception(f"Could not find kid {kid} among {key['kid'] for key in KEYS}")
    verified_body = jwt.decode(
        id_token, key, access_token=access_token, audience=CLIENT_ID
    )
    
    # Update the pending session with the username from the identity provider.
    username = verified_body["sub"]
    for pending_session in PENDING_SESSIONS:
        if pending_session.user_code == form_data["user_code"]:
            pending_session.username = username
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
        {"sub": pending_session.username, "type": "access"},
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

routes = [
    Route("/data", data, methods=["GET"]),
    Route("/authorize", authorize, methods=["POST"]),
    Route("/device_code_callback", device_code_callback, methods=["GET"]),
    Route("/device_code_form", handle_device_code_form, methods=["POST"]),
    Route("/token", token, methods=["POST"]),
    Route("/refresh", refresh, methods=["POST"])
]
app = Starlette(routes=routes)
