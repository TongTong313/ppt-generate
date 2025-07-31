#!/usr/bin/env python3
"""
基于MCP协议的动态注册客户端

这个客户端基于真正的MCP协议实现动态服务器注册和发现功能，
包含完整的工具发现、调用和管理机制。
"""

import asyncio
import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
from mcp_client import MCPClient, ServerConnection


@dataclass
class MCPServerRegistration:
    """MCP服务器注册信息"""

    name: str
    url: str
    description: str = ""
    tags: List[str] = None
    priority: int = 10
    auto_connect: bool = True
    health_check_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    last_seen: float = 0
    status: str = "unknown"  # unknown, healthy, unhealthy, connecting, disconnected

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.last_seen == 0:
            self.last_seen = time.time()


class MCPServiceRegistry:
    """MCP服务注册中心"""

    def __init__(self, registry_file: Optional[str] = None):
        self.registrations: Dict[str, MCPServerRegistration] = {}
        self.registry_file = registry_file
        self.callbacks: Dict[str, List[Callable]] = {
            "register": [],
            "unregister": [],
            "update": [],
            "status_change": [],
        }

        # 从文件加载注册信息
        if registry_file and Path(registry_file).exists():
            self.load_registry()

    def register_server(self, registration: MCPServerRegistration) -> bool:
        """注册MCP服务器"""
        try:
            old_registration = self.registrations.get(registration.name)
            if old_registration:
                # 更新现有注册信息
                self.registrations[registration.name] = registration
                event = "update"
            else:
                # 新增注册信息
                self.registrations[registration.name] = registration
                event = "register"

            # 触发回调
            self._trigger_callbacks(event, registration)

            # 保存到文件
            if self.registry_file:
                self.save_registry()

            logging.info(f"MCP服务器 {registration.name} 注册成功")
            return True

        except Exception as e:
            logging.error(f"注册MCP服务器 {registration.name} 失败: {str(e)}")
            return False

    def unregister_server(self, name: str) -> bool:
        """注销MCP服务器"""
        if name in self.registrations:
            registration = self.registrations.pop(name)
            self._trigger_callbacks("unregister", registration)

            if self.registry_file:
                self.save_registry()

            logging.info(f"MCP服务器 {name} 已注销")
            return True
        return False

    def update_server_status(self, name: str, status: str):
        """更新服务器状态"""
        if name in self.registrations:
            old_status = self.registrations[name].status
            self.registrations[name].status = status
            self.registrations[name].last_seen = time.time()

            if old_status != status:
                self._trigger_callbacks("status_change", self.registrations[name])

    def get_servers_by_tags(self, tags: List[str]) -> List[MCPServerRegistration]:
        """根据标签获取服务器"""
        result = []
        for registration in self.registrations.values():
            if any(tag in registration.tags for tag in tags):
                result.append(registration)
        return sorted(result, key=lambda x: x.priority, reverse=True)

    def get_all_servers(self) -> List[MCPServerRegistration]:
        """获取所有注册的服务器"""
        return list(self.registrations.values())

    def add_callback(self, event: str, callback: Callable):
        """添加事件回调"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, registration: MCPServerRegistration):
        """触发事件回调"""
        for callback in self.callbacks.get(event, []):
            try:
                callback(registration)
            except Exception as e:
                logging.error(f"回调执行失败: {str(e)}")

    def save_registry(self):
        """保存注册信息到文件"""
        if not self.registry_file:
            return

        try:
            data = {
                "servers": [asdict(reg) for reg in self.registrations.values()],
                "metadata": {"last_updated": time.time(), "version": "1.0"},
            }

            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logging.error(f"保存注册信息失败: {str(e)}")

    def load_registry(self):
        """从文件加载注册信息"""
        if not self.registry_file or not Path(self.registry_file).exists():
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            for server_data in data.get("servers", []):
                registration = MCPServerRegistration(**server_data)
                self.registrations[registration.name] = registration

            logging.info(f"从文件加载了 {len(self.registrations)} 个服务器注册信息")

        except Exception as e:
            logging.error(f"加载注册信息失败: {str(e)}")


class MCPServiceDiscovery:
    """MCP服务发现引擎"""

    def __init__(self, registry: MCPServiceRegistry):
        self.registry = registry
        self.running = False
        self.discovery_tasks: List[asyncio.Task] = []

    async def start_discovery(self, configs: List[Dict[str, Any]]):
        """启动服务发现"""
        self.running = True

        for config in configs:
            discovery_type = config.get("type")

            if discovery_type == "file_watch":
                task = asyncio.create_task(self._file_watch_discovery(config))
                self.discovery_tasks.append(task)
            elif discovery_type == "http_polling":
                task = asyncio.create_task(self._http_polling_discovery(config))
                self.discovery_tasks.append(task)
            elif discovery_type == "mcp_broadcast":
                task = asyncio.create_task(self._mcp_broadcast_discovery(config))
                self.discovery_tasks.append(task)

        logging.info(f"启动了 {len(self.discovery_tasks)} 个服务发现任务")

    async def stop_discovery(self):
        """停止服务发现"""
        self.running = False

        for task in self.discovery_tasks:
            task.cancel()

        await asyncio.gather(*self.discovery_tasks, return_exceptions=True)
        self.discovery_tasks.clear()

    async def _file_watch_discovery(self, config: Dict[str, Any]):
        """文件监控发现"""
        file_path = config["file_path"]
        interval = config.get("interval", 5)
        last_modified = 0

        while self.running:
            try:
                path = Path(file_path)
                if path.exists():
                    current_modified = path.stat().st_mtime
                    if current_modified > last_modified:
                        last_modified = current_modified
                        await self._process_discovery_file(file_path)

            except Exception as e:
                logging.error(f"文件监控发现错误: {str(e)}")

            await asyncio.sleep(interval)

    async def _http_polling_discovery(self, config: Dict[str, Any]):
        """HTTP轮询发现"""
        url = config["url"]
        interval = config.get("interval", 30)

        while self.running:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            await self._process_discovery_data(data)
                        else:
                            logging.warning(f"HTTP发现失败: {response.status}")

            except Exception as e:
                logging.error(f"HTTP轮询发现错误: {str(e)}")

            await asyncio.sleep(interval)

    async def _mcp_broadcast_discovery(self, config: Dict[str, Any]):
        """MCP广播发现（基于MCP协议的服务发现）"""
        # 这里可以实现基于MCP协议的服务发现机制
        # 例如通过特定的MCP工具来发现其他服务器
        pass

    async def _process_discovery_file(self, file_path: str):
        """处理发现文件"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            await self._process_discovery_data(data)
        except Exception as e:
            logging.error(f"处理发现文件失败: {str(e)}")

    async def _process_discovery_data(self, data: Dict[str, Any]):
        """处理发现的数据"""
        try:
            servers = data.get("servers", [])

            for server_data in servers:
                registration = MCPServerRegistration(
                    name=server_data["name"],
                    url=server_data["url"],
                    description=server_data.get("description", ""),
                    tags=server_data.get("tags", []),
                    priority=server_data.get("priority", 10),
                    auto_connect=server_data.get("auto_connect", True),
                    health_check_url=server_data.get("health_check_url"),
                    metadata=server_data.get("metadata", {}),
                )

                self.registry.register_server(registration)

        except Exception as e:
            logging.error(f"处理发现数据失败: {str(e)}")


class MCPDynamicClient(MCPClient):
    """基于MCP协议的动态注册客户端"""

    def __init__(
        self,
        registry_file: Optional[str] = None,
        api_key: str = None,
        base_url: str = None,
    ):
        super().__init__(api_key, base_url)

        # 初始化服务注册中心和发现引擎
        self.registry = MCPServiceRegistry(registry_file)
        self.discovery = MCPServiceDiscovery(self.registry)

        # 健康检查和清理任务
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        # 设置回调
        self.registry.add_callback("register", self._on_server_registered)
        self.registry.add_callback("unregister", self._on_server_unregistered)
        self.registry.add_callback("update", self._on_server_updated)
        self.registry.add_callback("status_change", self._on_server_status_changed)

    async def start_dynamic_features(
        self, discovery_configs: List[Dict[str, Any]] = None
    ):
        """启动动态功能"""
        # 启动服务发现
        if discovery_configs:
            await self.discovery.start_discovery(discovery_configs)

        # 启动健康检查
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        # 启动清理任务
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        logging.info("动态功能已启动")

    async def stop_dynamic_features(self):
        """停止动态功能"""
        # 停止服务发现
        await self.discovery.stop_discovery()

        # 停止健康检查
        if self.health_check_task:
            self.health_check_task.cancel()

        # 停止清理任务
        if self.cleanup_task:
            self.cleanup_task.cancel()

        logging.info("动态功能已停止")

    def register_server_manually(self, registration: MCPServerRegistration) -> bool:
        """手动注册MCP服务器"""
        return self.registry.register_server(registration)

    def unregister_server_manually(self, name: str) -> bool:
        """手动注销MCP服务器"""
        return self.registry.unregister_server(name)

    def get_registered_servers(
        self, tags: List[str] = None
    ) -> List[MCPServerRegistration]:
        """获取已注册的服务器"""
        if tags:
            return self.registry.get_servers_by_tags(tags)
        return self.registry.get_all_servers()

    async def connect_registered_servers(self):
        """连接所有已注册且启用自动连接的服务器"""
        servers_to_connect = [
            reg
            for reg in self.registry.get_all_servers()
            if reg.auto_connect and reg.name not in self.servers
        ]

        for registration in servers_to_connect:
            try:
                self.add_server(registration.name, registration.url)
                await self.connect_server(registration.name)
                self.registry.update_server_status(registration.name, "healthy")
            except Exception as e:
                logging.error(f"连接服务器 {registration.name} 失败: {str(e)}")
                self.registry.update_server_status(registration.name, "unhealthy")

    async def discover_and_call_tools(self, query: str) -> str:
        """发现工具并处理查询（增强版）"""
        # 首先获取所有已连接服务器的工具
        all_tools_by_server = await self.get_all_tools()

        # 创建工具发现工具
        discovery_tools = self._create_discovery_tools()

        # 合并所有工具
        available_tools = []

        # 添加MCP服务器工具
        for server_name, tools in all_tools_by_server.items():
            for tool in tools:
                available_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": f"[MCP:{server_name}] {tool.description}",
                            "parameters": tool.inputSchema,
                        },
                    }
                )

        # 添加发现和管理工具
        available_tools.extend(discovery_tools)

        if not available_tools:
            return "⚠️ 没有可用的工具，请确保至少有一个服务器已连接"

        # 处理查询
        return await self._process_query_with_tools(
            query, available_tools, all_tools_by_server
        )

    def _create_discovery_tools(self) -> List[Dict[str, Any]]:
        """创建服务发现和管理工具"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "discover_mcp_servers",
                    "description": "发现可用的MCP服务器",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "tags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "按标签过滤服务器",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_server_status",
                    "description": "获取MCP服务器状态信息",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {
                                "type": "string",
                                "description": "服务器名称，可选",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "connect_mcp_server",
                    "description": "连接到指定的MCP服务器",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "server_name": {
                                "type": "string",
                                "description": "要连接的服务器名称",
                            }
                        },
                        "required": ["server_name"],
                    },
                },
            },
        ]

    async def _process_query_with_tools(
        self, query: str, available_tools: List[Dict], all_tools_by_server: Dict
    ) -> str:
        """使用工具处理查询"""
        messages = [{"role": "user", "content": query}]

        print(f"🔧 可用工具数量: {len(available_tools)}")

        # 第一次调用大模型
        response = await self.llm.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        messages.append(response.choices[0].message)

        # 处理工具调用
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_call_id = tool_call.id

                print(f"🔧 工具调用: {tool_name}, 参数: {tool_args}")

                # 处理内置发现工具
                if tool_name in [
                    "discover_mcp_servers",
                    "get_server_status",
                    "connect_mcp_server",
                ]:
                    result = await self._handle_discovery_tool(tool_name, tool_args)
                    messages.append(
                        {
                            "role": "tool",
                            "content": result,
                            "tool_call_id": tool_call_id,
                        }
                    )
                else:
                    # 处理MCP服务器工具
                    server_name = self._find_tool_server(tool_name, all_tools_by_server)

                    if server_name and server_name in self.servers:
                        try:
                            result = await self.servers[server_name].call_tool(
                                tool_name, tool_args
                            )
                            print(
                                f"✅ 工具 {tool_name} 在服务器 {server_name} 上执行成功"
                            )

                            messages.append(
                                {
                                    "role": "tool",
                                    "content": result.content,
                                    "tool_call_id": tool_call_id,
                                }
                            )
                        except Exception as e:
                            error_msg = f"工具 {tool_name} 在服务器 {server_name} 上执行失败: {str(e)}"
                            print(f"❌ {error_msg}")

                            messages.append(
                                {
                                    "role": "tool",
                                    "content": [{"type": "text", "text": error_msg}],
                                    "tool_call_id": tool_call_id,
                                }
                            )
                    else:
                        error_msg = f"找不到工具 {tool_name} 对应的服务器"
                        print(f"❌ {error_msg}")

                        messages.append(
                            {
                                "role": "tool",
                                "content": [{"type": "text", "text": error_msg}],
                                "tool_call_id": tool_call_id,
                            }
                        )

        # 第二次调用大模型获取最终回复
        response = await self.llm.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )

        return response.choices[0].message.content

    async def _handle_discovery_tool(self, tool_name: str, tool_args: Dict) -> str:
        """处理发现工具调用"""
        if tool_name == "discover_mcp_servers":
            tags = tool_args.get("tags", [])
            servers = self.get_registered_servers(tags)

            result = {
                "servers": [
                    {
                        "name": server.name,
                        "url": server.url,
                        "description": server.description,
                        "tags": server.tags,
                        "status": server.status,
                        "priority": server.priority,
                    }
                    for server in servers
                ],
                "total": len(servers),
            }
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "get_server_status":
            server_name = tool_args.get("server_name")

            if server_name:
                # 获取特定服务器状态
                servers = [
                    reg
                    for reg in self.registry.get_all_servers()
                    if reg.name == server_name
                ]
            else:
                # 获取所有服务器状态
                servers = self.registry.get_all_servers()

            result = {
                "servers": [
                    {
                        "name": server.name,
                        "status": server.status,
                        "last_seen": server.last_seen,
                        "connected": server.name in self.servers
                        and self.servers[server.name].is_connected,
                    }
                    for server in servers
                ]
            }
            return json.dumps(result, ensure_ascii=False)

        elif tool_name == "connect_mcp_server":
            server_name = tool_args["server_name"]

            # 查找注册信息
            registration = None
            for reg in self.registry.get_all_servers():
                if reg.name == server_name:
                    registration = reg
                    break

            if not registration:
                return f"错误：找不到名为 {server_name} 的服务器注册信息"

            try:
                # 添加并连接服务器
                if server_name not in self.servers:
                    self.add_server(server_name, registration.url)

                await self.connect_server(server_name)
                self.registry.update_server_status(server_name, "healthy")

                return f"成功连接到服务器 {server_name}"

            except Exception as e:
                self.registry.update_server_status(server_name, "unhealthy")
                return f"连接服务器 {server_name} 失败: {str(e)}"

        return "未知的发现工具"

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"健康检查错误: {str(e)}")

    async def _perform_health_check(self):
        """执行健康检查"""
        for registration in self.registry.get_all_servers():
            try:
                if registration.health_check_url:
                    # 使用自定义健康检查URL
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            registration.health_check_url, timeout=10
                        ) as response:
                            if response.status == 200:
                                self.registry.update_server_status(
                                    registration.name, "healthy"
                                )
                            else:
                                self.registry.update_server_status(
                                    registration.name, "unhealthy"
                                )
                else:
                    # 检查MCP连接状态
                    if registration.name in self.servers:
                        server = self.servers[registration.name]
                        if server.is_connected:
                            # 尝试获取工具列表来验证连接
                            try:
                                await server.get_tools()
                                self.registry.update_server_status(
                                    registration.name, "healthy"
                                )
                            except Exception:
                                self.registry.update_server_status(
                                    registration.name, "unhealthy"
                                )
                        else:
                            self.registry.update_server_status(
                                registration.name, "disconnected"
                            )
                    else:
                        self.registry.update_server_status(
                            registration.name, "disconnected"
                        )

            except Exception as e:
                logging.error(f"健康检查服务器 {registration.name} 失败: {str(e)}")
                self.registry.update_server_status(registration.name, "unhealthy")

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"清理任务错误: {str(e)}")

    async def _perform_cleanup(self):
        """执行清理任务"""
        current_time = time.time()

        # 清理长时间未响应的服务器
        for registration in list(self.registry.get_all_servers()):
            if current_time - registration.last_seen > 3600:  # 1小时未响应
                if registration.status == "unhealthy":
                    logging.info(f"清理长时间未响应的服务器: {registration.name}")
                    # 可以选择注销或标记为离线
                    self.registry.update_server_status(registration.name, "offline")

    def _on_server_registered(self, registration: MCPServerRegistration):
        """服务器注册回调"""
        logging.info(f"MCP服务器注册事件: {registration.name}")

        # 如果设置了自动连接，则尝试连接
        if registration.auto_connect:
            asyncio.create_task(self._auto_connect_server(registration))

    def _on_server_unregistered(self, registration: MCPServerRegistration):
        """服务器注销回调"""
        logging.info(f"MCP服务器注销事件: {registration.name}")

        # 断开连接并移除
        asyncio.create_task(self._auto_disconnect_server(registration.name))

    def _on_server_updated(self, registration: MCPServerRegistration):
        """服务器更新回调"""
        logging.info(f"MCP服务器更新事件: {registration.name}")

        # 如果URL发生变化，需要重新连接
        if registration.name in self.servers:
            current_url = self.servers[registration.name].url
            if current_url != registration.url:
                asyncio.create_task(self._reconnect_server(registration))

    def _on_server_status_changed(self, registration: MCPServerRegistration):
        """服务器状态变化回调"""
        logging.info(f"MCP服务器状态变化: {registration.name} -> {registration.status}")

    async def _auto_connect_server(self, registration: MCPServerRegistration):
        """自动连接服务器"""
        try:
            if registration.name not in self.servers:
                self.add_server(registration.name, registration.url)

            await self.connect_server(registration.name)
            self.registry.update_server_status(registration.name, "healthy")

            logging.info(f"自动连接服务器成功: {registration.name}")
        except Exception as e:
            logging.error(f"自动连接服务器失败 {registration.name}: {str(e)}")
            self.registry.update_server_status(registration.name, "unhealthy")

    async def _auto_disconnect_server(self, server_name: str):
        """自动断开服务器"""
        try:
            if server_name in self.servers:
                await self.disconnect_server(server_name)
                self.remove_server(server_name)

            logging.info(f"自动断开服务器: {server_name}")
        except Exception as e:
            logging.error(f"自动断开服务器失败 {server_name}: {str(e)}")

    async def _reconnect_server(self, registration: MCPServerRegistration):
        """重新连接服务器"""
        try:
            # 先断开
            await self.disconnect_server(registration.name)
            self.remove_server(registration.name)

            # 重新添加和连接
            self.add_server(registration.name, registration.url)
            await self.connect_server(registration.name)
            self.registry.update_server_status(registration.name, "healthy")

            logging.info(f"重新连接服务器成功: {registration.name}")
        except Exception as e:
            logging.error(f"重新连接服务器失败 {registration.name}: {str(e)}")
            self.registry.update_server_status(registration.name, "unhealthy")

    def show_registry_status(self):
        """显示注册状态"""
        print("\n📋 MCP服务器注册状态:")
        print("-" * 60)

        servers = self.registry.get_all_servers()
        if not servers:
            print("  没有注册任何服务器")
            return

        for registration in sorted(servers, key=lambda x: x.priority, reverse=True):
            status_icon = {
                "healthy": "🟢",
                "unhealthy": "🔴",
                "connecting": "🟡",
                "disconnected": "⚪",
                "offline": "⚫",
                "unknown": "❓",
            }.get(registration.status, "❓")

            connected = (
                registration.name in self.servers
                and self.servers[registration.name].is_connected
            )
            connection_status = "已连接" if connected else "未连接"

            print(
                f"  {status_icon} {registration.name}: {registration.status} ({connection_status})"
            )
            print(f"     URL: {registration.url}")
            print(f"     标签: {', '.join(registration.tags)}")
            print(f"     优先级: {registration.priority}")
            if registration.description:
                print(f"     描述: {registration.description}")
            print()

        print(f"总计: {len(servers)} 个服务器已注册")

    async def chat_loop(self):
        """增强的交互式聊天循环"""
        print("\n🚀 MCP动态客户端启动！")
        print("输入 'quit' 或 '再见' 退出")
        print("输入 'status' 查看服务器状态")
        print("输入 'registry' 查看注册状态")
        print("输入 'tools' 查看可用工具")
        print("输入 'discover' 发现新服务器")

        while True:
            try:
                query = input("\n请输入问题: ").strip()

                if query.lower() == "quit" or query == "再见":
                    break
                elif query.lower() == "status":
                    self.show_status()
                    continue
                elif query.lower() == "registry":
                    self.show_registry_status()
                    continue
                elif query.lower() == "tools":
                    await self._show_tools()
                    continue
                elif query.lower() == "discover":
                    await self._manual_discovery()
                    continue

                response = await self.discover_and_call_tools(query)
                print(f"\n🤖 回复: {response}")

            except Exception as e:
                print(f"\n❌ 错误: {str(e)}")

    async def _manual_discovery(self):
        """手动发现服务器"""
        print("\n🔍 手动发现服务器...")

        # 这里可以实现手动发现逻辑
        # 例如扫描本地网络、查询注册中心等

        print("发现功能正在开发中...")

    async def cleanup(self):
        """清理所有连接和任务"""
        await self.stop_dynamic_features()
        await self.disconnect_all_servers()


# 使用示例
async def example_usage():
    """使用示例"""
    client = MCPDynamicClient(registry_file="mcp_registry.json")

    try:
        # 手动注册一些服务器
        weather_server = MCPServerRegistration(
            name="weather",
            url="http://localhost:8001",
            description="天气查询服务",
            tags=["weather", "api"],
            priority=10,
            auto_connect=True,
        )

        client.register_server_manually(weather_server)

        # 启动动态功能
        discovery_configs = [
            {
                "type": "file_watch",
                "file_path": "discovered_servers.json",
                "interval": 5,
            }
        ]

        await client.start_dynamic_features(discovery_configs)

        # 连接已注册的服务器
        await client.connect_registered_servers()

        # 显示状态
        client.show_registry_status()
        client.show_status()

        # 开始聊天循环
        await client.chat_loop()

    finally:
        await client.cleanup()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(example_usage())
