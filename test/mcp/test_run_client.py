# 测试MCP客户端

import asyncio
from ppt_generate.mcp_client import MCPClient


async def main():
    client = MCPClient()
    # pdf_to_text
    client.add_server(name="pdf_to_text", url="http://127.0.0.1:8888/mcp")
    # get_current_time
    client.add_server(name="get_current_time", url="http://127.0.0.1:8889/mcp")

    try:
        # 连接所有服务器
        await client.connect_all_servers()

        # 显示状态
        client.show_status()

        # 开始聊天循环
        await client.chat_loop()

    finally:
        # 清理连接
        await client.cleanup()

    # try:
    #     await client.connect_to_streamable_http_server(f"http://127.0.0.1:8888/mcp")
    #     await client.chat_loop()
    # except Exception as e:
    #     print(f"Error: {str(e)}")
    # finally:
    #     print("MCP Client Stopped!")
    #     await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
