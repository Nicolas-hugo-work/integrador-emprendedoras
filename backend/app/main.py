"""Composición de la aplicación FastAPI.

Este módulo solo crea la aplicación, configura middleware, traduce errores de
aplicación a respuestas HTTP y registra routers. Los casos de uso viven en
`app/services/` y el protocolo HTTP en `app/routers/`.

Se conserva `app = create_app()` para que `uvicorn app.main:app` y la imagen de
Docker sigan funcionando sin cambios.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import AppError
from app.routers import account, assistant, auth, businesses, finance, privacy, sources, system

#: El orden determina el de las rutas en el documento OpenAPI.
ROUTERS = (system, auth, account, businesses, finance, assistant, privacy, sources)


def create_app() -> FastAPI:
    """Construye la aplicación con su middleware, errores y routers."""
    settings = get_settings()
    application = FastAPI(title=settings.app_name, version="0.3.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AppError)
    def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Traduce los errores de aplicación al formato `{"detail": ...}`.

        Starlette recorre el MRO de la excepción, así que este único manejador
        cubre todas las subclases de `AppError`.
        """
        return JSONResponse(status_code=exc.status, content={"detail": exc.detail})

    for module in ROUTERS:
        application.include_router(module.router)
    return application


app = create_app()
