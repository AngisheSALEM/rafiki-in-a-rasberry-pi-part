"""
Main entrypoint launcher for Raspberry Pi Vision Microservice.
"""
import argparse
import uvicorn
import sys
from rpi_vision.config import settings

def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi Vision Capture Microservice")
    parser.add_argument("--host", type=str, default=settings.HOST, help="Host address to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=settings.PORT, help="Port to bind (default: 8000)")
    parser.add_argument("--camera-type", type=str, choices=["auto", "opencv", "picamera2", "mock"], default=settings.CAMERA_TYPE, help="Camera implementation type")
    parser.add_argument("--camera-index", type=str, default=settings.CAMERA_INDEX, help="USB camera index (e.g. 0) or RTSP URL")
    parser.add_argument("--width", type=int, default=settings.DEFAULT_WIDTH, help="Default capture width")
    parser.add_argument("--height", type=int, default=settings.DEFAULT_HEIGHT, help="Default capture height")
    parser.add_argument("--api-key", type=str, default=settings.API_KEY, help="Optional X-API-Key required for requests")
    
    args = parser.parse_args()

    settings.HOST = args.host
    settings.PORT = args.port
    settings.CAMERA_TYPE = args.camera_type
    settings.CAMERA_INDEX = args.camera_index
    settings.DEFAULT_WIDTH = args.width
    settings.DEFAULT_HEIGHT = args.height
    if args.api_key:
        settings.API_KEY = args.api_key

    print("===============================================================")
    print("      RASPBERRY PI VISION CAPTURE MICROSERVICE                ")
    print("===============================================================")
    print(f" Host:           http://{settings.HOST}:{settings.PORT}")
    print(f" Camera Mode:    {settings.CAMERA_TYPE}")
    print(f" Camera Index:   {settings.CAMERA_INDEX}")
    print(f" Resolution:     {settings.DEFAULT_WIDTH}x{settings.DEFAULT_HEIGHT}")
    print(f" API Key Check:  {'ENABLED' if settings.API_KEY else 'DISABLED'}")
    print("---------------------------------------------------------------")
    print(f" OpenAPI Docs:   http://localhost:{settings.PORT}/docs")
    print("===============================================================\n")

    uvicorn.run(
        "rpi_vision.api.app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
