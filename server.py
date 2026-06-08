import asyncio
import os
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import StreamingResponse
from mcp.server.fastmcp import FastMCP

from authsec_sdk import from_env, mount_mcp, ManifestTool
from authsec_sdk.runtime import Config, PolicyMode, ValidationMode
from dotenv import load_dotenv

# ── 1. Define your tools ─────────────────────────────────────────────
mcp = FastMCP("my-server")

@mcp.tool()
def add_no(a: float, b: float) -> float:
    return a + b


@mcp.tool()
def multiply_no(a: float, b: float) -> float:
    return a * b

# ── 2. Tell AuthSec about your tools (manifest) ──────────────────────
def my_tools():
    return [
        ManifestTool(
            name="add_no",
            description="Add two numbers",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        ),
        ManifestTool(
            name="multiply_no",
            description="Multiply two numbers",
            input_schema={
                "type": "object",
                "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
                "required": ["a", "b"],
            },
        ),
    ]

# ── 3. Config — from env vars or explicit ────────────────────────────
load_dotenv()
cfg = from_env()
cfg.tool_inventory_provider = my_tools

# ── 4. ASGI adapter (required on sdk-v2) ────────────────────────────
asgi_app = mcp.streamable_http_app()

async def mcp_handler(request: Request) -> StreamingResponse:
    resp_status = [500]
    resp_raw_headers = [[]]
    headers_ready = asyncio.Event()
    body_queue: asyncio.Queue = asyncio.Queue()

    async def _send(message: dict) -> None:
        if message["type"] == "http.response.start":
            resp_status[0] = message["status"]
            resp_raw_headers[0] = list(message.get("headers", []))
            headers_ready.set()
        elif message["type"] == "http.response.body":
            chunk = message.get("body", b"")
            if chunk:
                await body_queue.put(chunk)
            if not message.get("more_body", False):
                await body_queue.put(None)

    task = asyncio.ensure_future(asgi_app(request.scope, request._receive, _send))

    def _on_done(t):
        if not headers_ready.is_set():
            headers_ready.set()
        body_queue.put_nowait(None)

    task.add_done_callback(_on_done)
    await headers_ready.wait()

    out_headers = {
        k.decode(): v.decode()
        for k, v in resp_raw_headers[0]
        if k.lower() != b"content-length"
    }

    async def _body_gen():
        while True:
            chunk = await body_queue.get()
            if chunk is None:
                break
            yield chunk
        if not task.done():
            await task

    return StreamingResponse(_body_gen(), status_code=resp_status[0], headers=out_headers)

# ── 5. Mount ─────────────────────────────────────────────────────────
app = FastAPI()
mount_mcp(app, "/mcp", mcp_handler, cfg)   # handler = adapter, NOT asgi_app directly

