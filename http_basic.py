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
        return False
    username, _, password = base64.b64decode(param).decode().partition(":")
    return check_password(username, password)

def data(request):
    if not authenticate(request):
        return JSONResponse({"error": "..."}, status_code=401)
    return JSONResponse({"data": [1, 2, 3]})

routes = [Route("/data", data)]
app = Starlette(routes=routes)
