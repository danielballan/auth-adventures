import os
from secrets import compare_digest

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

SINGLE_USER_API_KEY = os.environ["API_KEY"]

def authenticate(request):
    # Check the 'Authorization' header and the 'api_key' query param.
    if "Authorization" in request.headers:
        # Verify Authorization header is "Apikey {SINGLE_USER_API_KEY}"
        authorization_header = request.headers["Authorization"]
        scheme, _, param = authorization_header.partition(" ")
        return (scheme.lower() == "apikey") and compare_digest(param, SINGLE_USER_API_KEY)
    if "api_key" in request.query_params:
        # Verify that api_key query params is SINGLE_USER_API_KEY.
        param = request.query_params["api_key"]
        return compare_digest(param, SINGLE_USER_API_KEY)
    return False


def data(request):
    if not authenticate(request):
        return JSONResponse({"error": "..."}, status_code=401)
    return JSONResponse({"data": [1, 2, 3]})

routes = [Route("/data", data)]
app = Starlette(routes=routes)
