"""MCP JSON-RPC 2.0 protocol helpers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

PROTOCOL_VERSION = "2025-03-26"
SERVER_NAME = "rentanagent"
SERVER_VERSION = "1.0.0"

# JSON-RPC 2.0 error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


@dataclass
class MCPRequest:
    jsonrpc: str
    method: str
    id: Optional[Any] = None
    params: Optional[dict] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MCPRequest":
        if data.get("jsonrpc") != "2.0":
            raise ValueError("Invalid JSON-RPC version")
        return cls(
            jsonrpc=data["jsonrpc"],
            method=data.get("method", ""),
            id=data.get("id"),
            params=data.get("params"),
        )


@dataclass
class MCPError:
    code: int
    message: str
    data: Optional[Any] = None

    def to_dict(self) -> dict:
        d: dict = {"code": self.code, "message": self.message}
        if self.data is not None:
            d["data"] = self.data
        return d


@dataclass
class MCPResponse:
    id: Any
    result: Optional[Any] = None
    error: Optional[MCPError] = None

    def to_dict(self) -> dict:
        d: dict = {"jsonrpc": "2.0", "id": self.id}
        if self.error is not None:
            d["error"] = self.error.to_dict()
        else:
            d["result"] = self.result
        return d


def build_initialize_result() -> dict:
    return {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
    }


def build_tools_list(tools: list[dict]) -> dict:
    return {"tools": tools}


def error_response(req_id: Any, code: int, message: str, data: Any = None) -> dict:
    return MCPResponse(id=req_id, error=MCPError(code=code, message=message, data=data)).to_dict()


def success_response(req_id: Any, result: Any) -> dict:
    return MCPResponse(id=req_id, result=result).to_dict()
