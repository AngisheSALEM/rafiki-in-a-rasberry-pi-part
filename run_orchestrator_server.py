#!/usr/bin/env python3
"""
Launcher script for the Rafiki Orchestrator Server & Hardware Bridge.
Runs on PC (10.20.20.224:7860).
"""
import argparse
import sys
import uvicorn

def main():
    parser = argparse.ArgumentParser(description="Rafiki Orchestrator Server & Hardware Bridge")
    parser.add_argument("--host", default="0.0.0.0", help="Host address (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=7860, help="Port to listen on (default: 7860)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print("===============================================================")
    print("      RAFIKI ORCHESTRATOR SERVER & HARDWARE BRIDGE            ")
    print("===============================================================")
    print(f" Host:                  http://{args.host}:{args.port}")
    print(f" Body Pull Endpoint:    http://{args.host}:{args.port}/api/body/next")
    print(f" Body Status Endpoint:  http://{args.host}:{args.port}/api/body/status")
    print(f" Vision Reg Endpoint:   http://{args.host}:{args.port}/api/vision/register")
    print(f" Orchestrate Endpoint:  http://{args.host}:{args.port}/api/orchestration/step")
    print("---------------------------------------------------------------")
    print(f" OpenAPI Docs:          http://localhost:{args.port}/docs")
    print("===============================================================\n")

    uvicorn.run(
        "orchestrator.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )

if __name__ == "__main__":
    main()
