from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from openai import AsyncOpenAI
import os


class MCPClient:
    """MCP Client for interacting with an MCP Streamable HTTP server"""

    def __init__(
            self,
            api_key: str = os.getenv("DASHSCOPE_API_KEY", ""),
            base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        # 初始化会话和客户端对象
        self.session: Optional[ClientSession] = None
        self.llm = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def connect_to_streamable_http_server(
        self,
        server_url: str,
    ):
        """
        连接到运行 HTTP Streamable 传输的 MCP 服务器
        
        Args:
            server_url: MCP 服务器的 URL 地址
            headers: 可选的 HTTP 请求头字典
        """
        # 创建 HTTP 流式传输客户端上下文
        # 使用 streamablehttp_client 建立与服务器的连接
        self._streams_context = streamablehttp_client(url=server_url)

        # 异步进入流上下文管理器，获取读写流
        # read_stream: 用于从服务器读取数据的流
        # write_stream: 用于向服务器写入数据的流
        # 第三个返回值用 _ 忽略（通常是连接信息）
        read_stream, write_stream, _ = await self._streams_context.__aenter__()

        # 使用读写流创建 MCP 客户端会话上下文
        # ClientSession 是 MCP 协议的核心会话对象
        self._session_context = ClientSession(read_stream, write_stream)

        # 异步进入会话上下文管理器，获取活跃的会话对象
        # 这个会话将用于后续的工具调用和消息处理
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        # print(response)
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
        } for tool in response.tools]

        # 和大模型对话
        response = await self.llm.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )
        print(response)

        # # Process response and handle tool calls
        # final_text = []

        # for content in response.content:
        #     if content.type == "text":
        #         final_text.append(content.text)
        #     elif content.type == "tool_use":
        #         tool_name = content.name
        #         tool_args = content.input

        #         # Execute tool call
        #         result = await self.session.call_tool(tool_name, tool_args)
        #         final_text.append(
        #             f"[Calling tool {tool_name} with args {tool_args}]")

        #         # Continue conversation with tool results
        #         if hasattr(content, "text") and content.text:
        #             messages.append({
        #                 "role": "assistant",
        #                 "content": content.text
        #             })
        #         messages.append({"role": "user", "content": result.content})

        #         # Get next response from Claude
        #         response = self.anthropic.messages.create(
        #             model="claude-3-5-sonnet-20241022",
        #             max_tokens=1000,
        #             messages=messages,
        #         )

        #         final_text.append(response.content[0].text)

        # return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:  # pylint: disable=W0125
            await self._streams_context.__aexit__(None, None, None)
