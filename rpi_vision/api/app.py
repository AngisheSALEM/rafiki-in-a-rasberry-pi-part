"""
FastAPI Application Setup & Lifespan Management.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router, set_global_camera
from ..config import settings
from ..camera.factory import create_camera

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("rpi_vision.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle context manager to open camera hardware on startup and release on shutdown."""
    logger.info(f"Starting Raspberry Pi Vision Service ({settings.DEVICE_NAME})...")
    
    camera_instance = create_camera(
        camera_type=settings.CAMERA_TYPE,
        camera_index=settings.parsed_camera_index,
        device_name=settings.DEVICE_NAME,
        width=settings.DEFAULT_WIDTH,
        height=settings.DEFAULT_HEIGHT
    )
    set_global_camera(camera_instance)

    yield

    logger.info("Shutting down Raspberry Pi Vision Service and releasing hardware...")
    if camera_instance:
        camera_instance.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Raspberry Pi Vision Capture Microservice",
        description="High-performance camera microservice designed to provide vision captures for LLM Orchestrators.",
        version="1.0.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
