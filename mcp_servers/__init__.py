"""
mcp_servers/__init__.py — Package marker for MCP server modules.

Three servers:
  db_server.py     → port 8001  (SQL query tools)
  search_server.py → port 8002  (web search tools)
  files_server.py  → port 8003  (sandboxed file tools)

Each server is started independently via docker-compose command: override.
All three read MCP_SERVER_KEY from env for shared bearer key auth.
"""
