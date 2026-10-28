"""SaagarDrishti Backend Application Entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app import __version__
from app.api.router import api_router
from app.core.config import settings


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Agentic AI-powered marine intelligence platform for the Karnataka coast.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Allow cross-origin requests for local frontend/dashboard development
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    application.include_router(api_router, prefix="/api")

    @application.get("/", tags=["Root"])
    async def root():
        """Root welcome endpoint."""
        return {
            "name": settings.APP_NAME,
            "version": __version__,
            "description": "Marine intelligence backend for the Karnataka coastline.",
            "docs_url": "/docs",
        }

    return application


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG,
    )
