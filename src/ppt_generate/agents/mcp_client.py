from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
from typing import Optional, Dict, List, Any, Literal
from openai import AsyncOpenAI
import os
import json
import asyncio


class ServerConnection:
    """单个MCP服务器连接的封装类"""

    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.session: Optional[ClientSession] = None
        self._streams_context = None
        self._session_context = None
        self.is_connected = False

    async def connect(self):
        """连接到MCP服务器"""
        try:
            # 创建 HTTP 流式传输客户端上下文
            self._streams_context = streamablehttp_client(url=self.url)

            # 异步进入流上下文管理器，获取读写流
            read_stream, write_stream, _ = await self._streams_context.__aenter__()

            # 使用读写流创建MCP客户端会话上下文
            self._session_context = ClientSession(read_stream, write_stream)

            # 异步进入会话上下文管理器，获取活跃的会话对象
            self.session = await self._session_context.__aenter__()

            # 初始化会话，执行MCP协议的初始化握手
            await self.session.initialize()

            self.is_connected = True
            print(f"✅ 成功连接到服务器: {self.name} ({self.url})")

        except Exception as e:
            print(f"❌ 连接服务器 {self.name} 失败: {str(e)}")
            self.is_connected = False
            raise

    async def disconnect(self):
        """断开与MCP服务器的连接"""
        try:
            if self._session_context:
                await self._session_context.__aexit__(None, None, None)
            if self._streams_context:
                await self._streams_context.__aexit__(None, None, None)

            self.is_connected = False
            print(f"🔌 已断开服务器连接: {self.name}")

        except Exception as e:
            print(f"⚠️ 断开服务器 {self.name} 连接时出错: {str(e)}")

    async def get_tools(self) -> List[Any]:
        """获取该服务器提供的工具列表"""
        if not self.is_connected or not self.session:
            raise RuntimeError(f"服务器 {self.name} 未连接")

        response = await self.session.list_tools()
        return response.tools

    async def call_tool(self, tool_name: str, tool_args: dict) -> Any:
        """调用该服务器的工具

        Args:
            tool_name (str): 工具名称
            tool_args (dict): 工具参数

        Returns:
            Any: 工具调用结果
        """
        if not self.is_connected or not self.session:
            raise RuntimeError(f"服务器 {self.name} 未连接")

        return await self.session.call_tool(tool_name, tool_args)


class MCPClient:
    """MCP客户端v2版本：支持多个MCP服务器
    智能体需要集成这个类来写代码，必须实现run_agent方法
    """

    def add_server(self, name: str, url: str) -> None:
        """添加一个MCP服务器"""
        if name in self.servers:
            print(f"⚠️ 服务器 {name} 已存在，将被替换")

        self.servers[name] = ServerConnection(name, url)
        print(f"📝 已添加服务器: {name} ({url})")

    def remove_server(self, name: str) -> None:
        """移除一个MCP服务器"""
        if name in self.servers:
            del self.servers[name]
            print(f"🗑️ 已移除服务器: {name}")
        else:
            print(f"⚠️ 服务器 {name} 不存在")

    async def connect_server(self, name: str):
        """连接指定的服务器"""
        if name not in self.servers:
            print(f"⚠️ 服务器 {name} 不存在")
            return False

        try:
            await self.servers[name].connect()
            return True
        except Exception:
            return False

    async def connect_all_servers(self):
        """连接所有已添加的服务器"""
        if not self.servers:
            print("⚠️ 没有可连接的服务器")
            return

        print(f"🔄 开始连接 {len(self.servers)} 个服务器...")

        # 并发连接所有服务器
        tasks = [server.connect() for server in self.servers.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计连接结果
        connected_count = sum(
            1 for server in self.servers.values() if server.is_connected
        )
        print(f"📊 连接完成: {connected_count}/{len(self.servers)} 个服务器连接成功")

    async def disconnect_server(self, name: str):
        """断开指定服务器的连接"""
        if name not in self.servers:
            print(f"⚠️ 服务器 {name} 不存在")
            return

        await self.servers[name].disconnect()

    async def disconnect_all_servers(self):
        """断开所有服务器连接"""
        print("🔌 正在断开所有服务器连接...")

        tasks = [server.disconnect() for server in self.servers.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

        print("✅ 所有服务器连接已断开")

    def get_connected_servers(self) -> List[str]:
        """获取已连接的服务器列表"""
        return [name for name, server in self.servers.items() if server.is_connected]

    async def get_all_tools(self) -> Dict[str, List[Any]]:
        """获取所有已连接服务器的工具"""
        all_tools = {}

        for name, server in self.servers.items():
            if server.is_connected:
                try:
                    tools = await server.get_tools()
                    all_tools[name] = tools
                except Exception as e:
                    print(f"⚠️ 获取服务器 {name} 的工具失败: {str(e)}")
                    all_tools[name] = []
            else:
                all_tools[name] = []

        return all_tools

    def _find_tool_server(
        self, tool_name: str, all_tools: Dict[str, List[Any]]
    ) -> Optional[str]:
        """根据工具名称找到对应的服务器

        Args:
            tool_name (str): 工具名称
            all_tools (Dict[str, List[Any]]): 所有服务器的工具列表

        Returns:
            Optional[str]: 找到的服务器名称，未找到返回None
        """
        for server_name, tools in all_tools.items():
            for tool in tools:
                if tool.name == tool_name:
                    return server_name
        return None

    def show_status(self) -> None:
        """显示所有服务器的连接状态"""
        print("\n📊 服务器连接状态:")
        print("-" * 50)

        if not self.servers:
            print("  没有配置任何服务器")
            return

        for name, server in self.servers.items():
            status = "🟢 已连接" if server.is_connected else "🔴 未连接"
            print(f"  {name}: {status} ({server.url})")

        connected_count = sum(
            1 for server in self.servers.values() if server.is_connected
        )
        print(f"\n总计: {connected_count}/{len(self.servers)} 个服务器已连接")

    async def _show_tools(self) -> None:
        """显示所有可用工具"""
        print("\n🔧 可用工具列表:")
        print("-" * 50)

        all_tools = await self.get_all_tools()

        for server_name, tools in all_tools.items():
            if tools:
                print(f"\n📡 服务器: {server_name}")
                for tool in tools:
                    print(f"  • {tool.name}: {tool.description.strip()}")
            else:
                print(f"\n📡 服务器: {server_name} (无可用工具或未连接)")

    async def cleanup(self) -> None:
        """清理所有连接"""
        await self.disconnect_all_servers()

    async def run_agent(self) -> None:
        """智能体运行逻辑，必须实现"""
        raise NotImplementedError("智能体必须实现run_agent方法")

    # async def process_query(self, query: str) -> str:
    #     """处理查询，使用所有可用的工具"""
    #     messages = [{"role": "user", "content": query}]

    #     # 获取所有服务器的工具
    #     all_tools_by_server = await self.get_all_tools()
    #     # print(all_tools_by_server)

    #     # 合并所有工具为OpenAI格式
    #     available_tools = []
    #     for server_name, tools in all_tools_by_server.items():
    #         for tool in tools:
    #             available_tools.append(
    #                 {
    #                     "type": "function",
    #                     "function": {
    #                         "name": tool.name,
    #                         "description": f"[{server_name}] {tool.description}",
    #                         "parameters": tool.inputSchema,
    #                     },
    #                 }
    #             )

    #     if not available_tools:
    #         print("⚠️ 没有可用的工具可正常使用，无法触发工具调用过程")

    #     print(f"🔧 可用工具数量: {len(available_tools)}")

    #     # 第一次调用大模型
    #     response = await self.llm.chat.completions.create(
    #         model=self.model,
    #         tool_choice=self.tool_choice,
    #         max_tokens=self.max_tokens,
    #         temperature=self.temperature,
    #         messages=messages,
    #         tools=available_tools,
    #     )

    #     messages.append(response.choices[0].message)

    #     # 处理工具调用
    #     if response.choices[0].message.tool_calls:
    #         for tool_call in response.choices[0].message.tool_calls:
    #             tool_name = tool_call.function.name
    #             tool_args = json.loads(tool_call.function.arguments)
    #             tool_call_id = tool_call.id

    #             print(f"🔧 工具调用: {tool_name}, 参数: {tool_args}")

    #             # 找到工具对应的服务器
    #             server_name = self._find_tool_server(tool_name, all_tools_by_server)

    #             if server_name and server_name in self.servers:
    #                 try:
    #                     result = await self.servers[server_name].call_tool(
    #                         tool_name, tool_args
    #                     )
    #                     print(f"✅ 工具 {tool_name} 在服务器 {server_name} 上执行成功")

    #                     messages.append(
    #                         {
    #                             "role": "tool",
    #                             "content": result.content,
    #                             "tool_call_id": tool_call_id,
    #                         }
    #                     )
    #                 except Exception as e:
    #                     error_msg = f"工具 {tool_name} 在服务器 {server_name} 上执行失败: {str(e)}"
    #                     print(f"❌ {error_msg}")

    #                     messages.append(
    #                         {
    #                             "role": "tool",
    #                             "content": error_msg,
    #                             "tool_call_id": tool_call_id,
    #                         }
    #                     )
    #             else:
    #                 error_msg = f"找不到工具 {tool_name} 对应的服务器"
    #                 print(f"❌ {error_msg}")

    #                 messages.append(
    #                     {
    #                         "role": "tool",
    #                         "content": error_msg,
    #                         "tool_call_id": tool_call_id,
    #                     }
    #                 )

    #     # 第二次调用大模型获取最终回复
    #     response = await self.llm.chat.completions.create(
    #         model=self.model,
    #         tool_choice=self.tool_choice,
    #         max_tokens=self.max_tokens,
    #         temperature=self.temperature,
    #         messages=messages,
    #         tools=available_tools,
    #     )

    #     return response.choices[0].message.content

    # async def chat_loop(self):
    #     """交互式聊天循环"""
    #     print("\n🚀 多服务器MCP客户端启动！")
    #     print("输入 'quit' 或 '再见' 退出")
    #     print("输入 'status' 查看服务器状态")
    #     print("输入 'tools' 查看可用工具")

    #     while True:
    #         try:
    #             query = input("\n请输入问题: ").strip()

    #             if query.lower() == "quit" or query == "再见":
    #                 break
    #             elif query.lower() == "status":
    #                 self.show_status()
    #                 continue
    #             elif query.lower() == "tools":
    #                 await self._show_tools()
    #                 continue

    #             response = await self.process_query(query)
    #             print(f"\n🤖 回复: {response}")

    #         except Exception as e:
    #             print(f"\n❌ 错误: {str(e)}")
