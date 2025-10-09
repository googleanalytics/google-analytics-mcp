# Copyright 2025 Google LLC All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Module declaring the singleton MCP instance.

The singleton allows other modules to register their tools with the same MCP
server using `@mcp.tool` annotations, thereby 'coordinating' the bootstrapping
of the server.
"""
#from mcp.server.fastmcp import FastMCP


import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from analytics_mcp.custom_header_middleware import CustomHeaderMiddleware

# Load Azure AD configuration
tenant_id = os.environ.get("AZURE_TENANT_ID")
client_id = os.environ.get("AZURE_CLIENT_ID")


if tenant_id and client_id:
    try:
        auth = JWTVerifier(
            jwks_uri=f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            issuer=f"https://sts.windows.net/{tenant_id}/",
            audience=client_id, 
            algorithm="RS256"
        )
        mcp = FastMCP("GA4 Prod", auth=auth)
        mcp.add_middleware(CustomHeaderMiddleware())
        print("JWT Verifier created successfully (no audience)")
    except Exception as e:
        print(f"JWT Verifier creation failed: {e}")
        mcp = FastMCP("GA4")
        mcp.add_middleware(CustomHeaderMiddleware())

else:
    mcp = FastMCP("Production Server - No Config")
    mcp.add_middleware(CustomHeaderMiddleware())


