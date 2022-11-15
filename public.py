from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

def data(request):
    return JSONResponse({"data": [1, 2, 3]})

routes = [Route("/data", data)]
app = Starlette(routes=routes)
