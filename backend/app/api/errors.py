from fastapi import Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, detail: str, code: str | None = None, status_code: int = 400):
        self.detail = detail
        self.code = code
        self.status_code = status_code

class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail=detail, code="not_found", status_code=404)

class AuthError(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(detail=detail, code="auth_error", status_code=401)

class PermissionError(AppException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail=detail, code="forbidden", status_code=403)

def register_exception_handlers(app):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "code": exc.code},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "code": "internal_error"},
        )
