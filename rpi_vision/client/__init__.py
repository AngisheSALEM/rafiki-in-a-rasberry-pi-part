"""
Client package for external LLM orchestrators.
"""
from .tool_wrapper import RpiVisionClient, get_vision_tool_definition

__all__ = ["RpiVisionClient", "get_vision_tool_definition"]
