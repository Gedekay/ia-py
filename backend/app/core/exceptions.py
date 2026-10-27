from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400) -> None:
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Ressource introuvable.") -> None:
        super().__init__("NOT_FOUND", message, 404)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Accès interdit.") -> None:
        super().__init__("FORBIDDEN", message, 403)


class ValidationError(AppException):
    def __init__(self, message: str) -> None:
        super().__init__("VALIDATION_ERROR", message, 422)


class ConstitutionalRefMissingError(AppException):
    def __init__(self, message: str) -> None:
        super().__init__("CONSTITUTIONAL_REFERENCE_MISSING", message, 503)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def handle_app_exception(request: Request, error: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=error.http_status,
            content={"code": error.code, "message": error.message, "request_id": getattr(request.state, "request_id", None)},
        )