from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from typing import Optional
from openai import AsyncOpenAI
import os
import json


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
        """
        # 创建 HTTP 流式传输客户端上下文
        # 使用 streamablehttp_client 建立与服务器的连接，此时还没有真正链接
        self._streams_context = streamablehttp_client(url=server_url)

        # 异步进入流上下文管理器，获取读写流
        # read_stream: 用于从服务器读取数据的流
        # write_stream: 用于向服务器写入数据的流
        read_stream, write_stream, _ = await self._streams_context.__aenter__()

        # 使用读写流创建MCP客户端会话上下文，让会话知道如何与服务器通信
        # ClientSession 是 MCP 协议的核心会话对象
        self._session_context = ClientSession(read_stream, write_stream)

        # 异步进入会话上下文管理器，获取活跃的会话对象
        # 这个会话将用于后续的工具调用和消息处理
        self.session: ClientSession = await self._session_context.__aenter__()

        # 初始化会话，执行MCP协议的初始化握手
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

        # 和大模型对话，先不考虑流式
        response = await self.llm.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        messages.append(response.choices[0].message)

        # 如果有工具调用
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                # 获取工具调用信息
                tool_name = tool_call.function.name
                tool_args = tool_call.function.arguments
                tool_call_id = tool_call.id
                # 解析tool_args，是json字符串，需要转换为字典
                tool_args = json.loads(tool_args)
                print(f"工具调用：{tool_name}, 参数：{tool_args}")

                # 这里的result是MCP协议字段，不可以直接用
                result = await self.session.call_tool(tool_name, tool_args)

                messages.append({
                    "role": "tool",
                    "content": result.content,
                    "tool_call_id": tool_call_id
                })

        # 有工具调用还要再让大模型输出一遍
        response = await self.llm.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        return response.choices[0].message.content

    async def chat_loop(self):
        """循环对话保证不中断"""
        print("\n童发发的MCP客户端启动！")
        print("输入'quit'或'再见'退出")

        while True:
            try:
                query = input("\n请输入问题：").strip()

                if query.lower() == "quit" or query == "再见":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """清理会话和流，两次 __aexit__() 是分别关闭协议层和传输层的资源。
        先关闭会话（协议层），再关闭流（传输层），这样可以保证资源释放的顺序和完整性。
        如果只关闭其中一个，另一个资源可能会泄漏，导致内存、网络连接等无法及时释放。
        """
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:  # pylint: disable=W0125
            await self._streams_context.__aexit__(None, None, None)
