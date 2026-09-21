"""Request ID, Logging, and Error Handling Middleware."""

import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.core.logging import logger
from app.utils.request_id import generate_request_id, set_current_request_id


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for propagating Request IDs, timing requests, and structured logging."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # Extract or generate Request ID
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        set_current_request_id(request_id)

        # Attempt to inspect customer ID from header or query param
        customer_id = request.headers.get("X-Customer-ID") or request.query_params.get("customer_id")
        try:
            parsed_customer_id = int(customer_id) if customer_id else None
        except (ValueError, TypeError):
            parsed_customer_id = None

        endpoint_str = f"{request.method} {request.url.path}"
        status_code = 500
        error_code = None

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Compute execution latency
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Attach headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time-MS"] = str(latency_ms)

            # Determine log level and error code if status >= 400
            if status_code >= 500:
                level = "ERROR"
                error_code = getattr(response, "error_code", "INTERNAL_SERVER_ERROR")
            elif status_code >= 400:
                level = "WARNING"
                error_code = getattr(response, "error_code", "CLIENT_ERROR")
            else:
                level = "INFO"

            logger.log(
                level=getattr(logger.level, level, 20) if hasattr(logger.level, level) else (40 if level == "ERROR" else 20),
                msg=f"HTTP {request.method} {request.url.path} responded {status_code} in {latency_ms}ms",
                extra={
                    "request_id": request_id,
                    "customer_id": parsed_customer_id,
                    "endpoint": endpoint_str,
                    "status_code": status_code,
                    "error_code": error_code,
                    "response_time_ms": latency_ms,
                    "service": "solutionbridge-gateway",
                },
            )

            return response

        except Exception as exc:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            error_code = "UNHANDLED_EXCEPTION"

            logger.error(
                f"Unhandled exception during {endpoint_str}: {str(exc)}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "customer_id": parsed_customer_id,
                    "endpoint": endpoint_str,
                    "status_code": 500,
                    "error_code": error_code,
                    "response_time_ms": latency_ms,
                    "service": "solutionbridge-gateway",
                },
            )

            # Do not expose raw internal stack traces to the caller
            return JSONResponse(
                status_code=500,
                content={
                    "status_code": 500,
                    "error": "Internal Server Error",
                    "error_code": error_code,
                    "message": "An unexpected server error occurred. Please contact solutions engineering with this request ID.",
                    "request_id": request_id,
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Response-Time-MS": str(latency_ms),
                },
            )
