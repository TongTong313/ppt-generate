# 测试MCP客户端

import asyncio
from ppt_generate.mcp_client_backup import MCPClient


async def main():
    client = MCPClient()

    try:
        await client.connect_to_streamable_http_server(f"http://127.0.0.1:8888/mcp")
        await client.chat_loop()
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        print("MCP Client Stopped!")
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
