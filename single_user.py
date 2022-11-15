import os
from secrets import compare_digest

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

SINGLE_USER_API_KEY = os.environ["API_KEY"]

def authenticate(request):
    # Verify Authorization header is "Apikey {SINGLE_USER_API_KEY}"
    authorization_header = request.headers.get("Authorization", "")
    scheme, _, param = authorization_header.partition(" ")
    return (scheme.lower() == "apikey") and compare_digest(param, SINGLE_USER_API_KEY)

def data(request):
    if not authenticate(request):
        return JSONResponse({"error": "..."}, status_code=401)
    return JSONResponse({"data": [1, 2, 3]})

routes = [Route("/data", data)]
app = Starlette(routes=routes)
