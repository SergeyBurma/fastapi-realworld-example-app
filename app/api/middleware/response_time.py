import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class ResponseTimeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        response = await call_next(request)
        end_time = time.perf_counter()
        time_taken = round((end_time - start_time) * 1000, 2)  # ms
        response.headers["X-REQUEST-TIME"] = f"{time_taken}ms"
        return response
