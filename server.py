from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
from authsec_sdk import from_env, mount_mcp, ManifestTool
import os

load_dotenv()

mcp = FastMCP("Python Setup Guide MCP Server")


@mcp.tool()
def get_setup_guide(language_version: str = "3.12") -> str:
    """Return a Python setup guide for the specified version."""
    return f"""# Python {language_version} Setup Guide

## Installation
1. Download Python {language_version} from python.org
2. Run the installer
3. Verify: python --version

## Virtual Environment
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\\Scripts\\activate    # Windows

## Package Management
pip install -r requirements.txt
"""


@mcp.tool()
def get_dependencies_template() -> str:
    """Return a template requirements.txt for a FastAPI + AuthSec project."""
    return """fastapi>=0.111.0
uvicorn[standard]>=0.30.0
authsec-sdk>=4.4.3
python-dotenv>=1.0.0
"""


@mcp.tool()
def get_authsec_integration_guide() -> str:
    """Return a step-by-step guide for integrating AuthSec into a Python FastAPI app."""
    return """# AuthSec + FastAPI Integration Guide

## 1. Install dependencies
pip install authsec-sdk fastapi uvicorn mcp python-dotenv

## 2. Register your resource server on AuthSec dashboard
- Go to https://dev.api.authsec.dev
- Create a resource server and note your UUID + secret

## 3. Set environment variables
AUTHSEC_ISSUER=https://dev.api.authsec.dev
AUTHSEC_INTROSPECTION_CLIENT_ID=<your-uuid>
AUTHSEC_INTROSPECTION_CLIENT_SECRET=<your-secret>
AUTHSEC_RESOURCE_URI=https://<your-service>.onrender.com/mcp

## 4. Use mount_mcp to protect your MCP endpoint
from authsec_sdk import from_env, mount_mcp
cfg = from_env()
mount_mcp(app, "/mcp", mcp_app, cfg)
"""


def my_tools() -> list[ManifestTool]:
    return [
        ManifestTool(
            name="get_setup_guide",
            description="Return a Python setup guide for a specified version",
            input_schema={
                "type": "object",
                "properties": {
                    "language_version": {"type": "string", "description": "Python version e.g. 3.12"},
                },
                "required": [],
            },
            suggested_scopes=["setup_guide:read"],
        ),
        ManifestTool(
            name="get_dependencies_template",
            description="Return a template requirements.txt for a FastAPI + AuthSec project",
            input_schema={"type": "object", "properties": {}},
            suggested_scopes=["setup_guide:read"],
        ),
        ManifestTool(
            name="get_authsec_integration_guide",
            description="Return a step-by-step guide for integrating AuthSec into a Python FastAPI app",
            input_schema={"type": "object", "properties": {}},
            suggested_scopes=["setup_guide:read"],
        ),
    ]


cfg = from_env()
cfg.tool_inventory_provider = my_tools
cfg.publish_manifest = True

app = FastAPI()
mcp_app = mcp.streamable_http_app()
mount_mcp(app, "/mcp", mcp_app, cfg)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        log_level="info",
    )
