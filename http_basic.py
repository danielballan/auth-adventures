import base64

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

def check_password(username, password):
    # Interact with some external system like PAM or LDAP....
    return password == "password"  # placeholder

def authenticate(request):
    # Verify Authorization header is "Basic {base64-encoded username:password}"
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    if scheme.lower() != "basic":
        return
    username, _, password = base64.b64decode(param).decode().partition(":")
    if check_password(username, password):
        return username

def data(request):
    username = authenticate(request)
    if not username:
        return JSONResponse({"error": "..."}, status_code=401)
    return JSONResponse({"data": [1, 2, 3], "who_am_i": username})

routes = [Route("/data", data)]
app = Starlette(routes=routes)
