import asyncio
from ppt_generate.tool.tool import pdf_to_text
from ppt_generate.tool.mcp_server import MCPServer


def main():
    mcp_server = MCPServer(funcs=[pdf_to_text])
    # 使用streamable-http传输，指定端口8888
    mcp_server.run(transport="streamable-http", mount_path="/mcp")


if __name__ == "__main__":
    asyncio.run(main())
