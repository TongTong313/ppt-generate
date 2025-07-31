import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
import aiohttp
import logging
from config_multi_mcp_client import ConfigurableMCPClient, ServerConfig


@dataclass
class ServerRegistration:
    """服务器注册信息

    Arg:
        name (str): 服务器名称
        url (str): 服务器URL
        description (str, optional): 服务器描述. Defaults to "".
        tags (List[str], optional): 服务器标签. Defaults to None.
        priority (int, optional): 服务器优先级. Defaults to 0.
        auto_connect (bool, optional): 是否自动连接. Defaults to True.
        health_check_url (Optional[str], optional): 健康检查URL. Defaults to None.
        metadata (Dict[str, Any], optional): 元数据. Defaults to None.
        registered_at (float, optional): 注册时间. Defaults to None.
        last_seen (float, optional): 服务器最后一次活跃的时间戳. Defaults to None.
    """

    name: str
    url: str
    description: str = ""
    tags: List[str] = None
    priority: int = 0  # 优先级，数字越大优先级越高
    auto_connect: bool = True
    health_check_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    registered_at: float = None
    last_seen: float = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = time.time()
        if self.last_seen is None:
            self.last_seen = time.time()


class ServiceRegistry:
    """服务注册类，用于管理服务注册信息

    Args:
        registry_file (Optional[str], optional): 注册文件路径. Defaults to None.
    """

    def __init__(self, registry_file: Optional[str] = None):
        # 服务注册信息
        self.registrations: Dict[str, ServerRegistration] = {}
        # 注册文件
        self.registry_file = registry_file
        # 注册回调
        self.callbacks: Dict[str, List[Callable]] = {
            "register": [],
            "unregister": [],
            "update": [],
        }

        # 从文件加载注册信息
        if registry_file and Path(registry_file).exists():
            self.load_registry()

    def register_server(self, registration: ServerRegistration) -> bool:
        """注册服务器

        Args:
            registration (ServerRegistration): 服务器注册信息

        Returns:
            bool: 注册是否成功
        """
        try:
            # 检查服务器是否已注册
            old_registration = self.registrations.get(registration.name, None)
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

            logging.info(f"服务器 {registration.name} 注册成功")
            return True

        except Exception as e:
            logging.error(f"注册服务器 {registration.name} 失败: {str(e)}")
            return False

    def unregister_server(self, server_name: str) -> bool:
        """注销服务器

        Args:
            server_name (str): 服务器名称

        Returns:
            bool: 注销是否成功
        """
        try:
            if server_name in self.registrations:
                registration = self.registrations.pop(server_name)

                # 触发回调
                self._trigger_callbacks("unregister", registration)

                # 保存到文件
                if self.registry_file:
                    self.save_registry()

                logging.info(f"服务器 {server_name} 注销成功")
                return True
            else:
                logging.warning(f"服务器 {server_name} 不存在")
                return False

        except Exception as e:
            logging.error(f"注销服务器 {server_name} 失败: {str(e)}")
            return False

    def get_servers(
        self, tags: List[str] = None, priority_threshold: int = 0
    ) -> List[ServerRegistration]:
        """获取服务器列表

        Args:
            tags (List[str], optional): 标签列表. Defaults to None.
            priority_threshold (int, optional): 优先级阈值. Defaults to 0.

        Returns:
            List[ServerRegistration]: 服务器列表
        """
        servers = list(self.registrations.values())

        # 按标签过滤
        if tags:
            servers = [s for s in servers if any(tag in s.tags for tag in tags)]

        # 按优先级过滤
        servers = [s for s in servers if s.priority >= priority_threshold]

        # 按优先级排序
        servers.sort(key=lambda x: x.priority, reverse=True)

        return servers

    def update_last_seen(self, server_name: str):
        """更新服务器最后活跃时间

        Args:
            server_name (str): 服务器名称
        """
        if server_name in self.registrations:
            self.registrations[server_name].last_seen = time.time()

    def get_stale_servers(self, timeout: int = 300) -> List[str]:
        """获取超时的服务器

        Args:
            timeout (int, optional): 超时时间（秒）. Defaults to 300.

        Returns:
            List[str]: 超时的服务器名称列表
        """
        current_time = time.time()
        stale_servers = []

        for name, registration in self.registrations.items():
            if current_time - registration.last_seen > timeout:
                stale_servers.append(name)

        return stale_servers

    def add_callback(self, event: str, callback: Callable) -> None:
        """添加事件回调

        Args:
            event (str): 事件类型，可选值为 "register", "unregister", "update"
            callback (Callable): 回调函数
        """
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callbacks(self, event: str, registration: ServerRegistration) -> None:
        """触发事件回调

        Args:
            event (str): 事件类型，可选值为 "register", "unregister", "update"
            registration (ServerRegistration): 服务器注册信息
        """
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
            # 转换注册信息为字典
            registry_data = {
                "servers": {
                    name: asdict(registration)
                    for name, registration in self.registrations.items()
                }
            }

            # 保存到文件
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump(registry_data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logging.error(f"保存注册信息失败: {str(e)}")

    def load_registry(self):
        """从文件加载注册信息"""
        if not self.registry_file or not Path(self.registry_file).exists():
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                registry_data = json.load(f)

            # 转换为ServerRegistration对象
            for name, data in registry_data.get("servers", {}).items():
                registration = ServerRegistration(**data)
                self.registrations[name] = registration

            logging.info(f"从文件加载了 {len(self.registrations)} 个服务器注册信息")

        except Exception as e:
            logging.error(f"加载注册信息失败: {str(e)}")


class ServiceDiscovery:
    """服务发现类，负责发现和管理服务实例，支持多种发现方式。

    Args:
        registry (ServiceRegistry): 服务注册中心实例

    Attributes:
        discovery_tasks (Dict[str, asyncio.Task]): 服务发现任务字典，键为发现类型和名称，值为任务对象
        running (bool): 服务发现是否正在运行
    """

    def __init__(self, registry: ServiceRegistry):
        self.registry = registry
        self.discovery_tasks: Dict[str, asyncio.Task] = {}
        self.running = False

    async def start_discovery(self, discovery_configs: List[Dict[str, Any]]):
        """启动服务发现

        Args:
            discovery_configs (List[Dict[str, Any]]): 服务发现配置列表
            举例：
                discovery_configs = [
                {
                    'type': 'file_watch',
                    'name': 'local_file_discovery',
                    'file_path': 'examples/discovered_servers.json',
                    'interval': 5  # 每5秒检查一次文件变化
                }
        ]
        """
        self.running = True

        for config in discovery_configs:
            # 检查发现类型是否支持
            discovery_type = config.get("type")
            if discovery_type not in ["http_polling", "file_watch", "multicast"]:
                logging.warning(f"不支持的发现类型: {discovery_type}")
                continue

            if discovery_type == "http_polling":  # 1. HTTP轮询发现
                task = asyncio.create_task(self._http_polling_discovery(config))
                self.discovery_tasks[
                    f"http_polling_{config.get('name', 'default')}"
                ] = task
            elif discovery_type == "file_watch":  # 2. 文件监控发现
                task = asyncio.create_task(self._file_watch_discovery(config))
                self.discovery_tasks[f"file_watch_{config.get('name', 'default')}"] = (
                    task
                )
            elif discovery_type == "multicast":  # 3. 组播发现
                task = asyncio.create_task(self._multicast_discovery(config))
                self.discovery_tasks[f"multicast_{config.get('name', 'default')}"] = (
                    task
                )

    async def stop_discovery(self):
        """停止服务发现"""
        self.running = False

        for task in self.discovery_tasks.values():
            task.cancel()

        await asyncio.gather(*self.discovery_tasks.values(), return_exceptions=True)
        self.discovery_tasks.clear()

    async def _http_polling_discovery(self, config: Dict[str, Any]):
        """HTTP轮询发现

        Args:
            config (Dict[str, Any]): 发现配置
            举例：
                config = {
                    'type': 'http_polling',
                    'name': 'http_discovery',
                    'url': 'http://localhost:8080/api/discover',
                    'interval': 30  # 每30秒轮询一次
                }
        """
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

    async def _file_watch_discovery(self, config: Dict[str, Any]):
        """文件监控发现

        Args:
            config (Dict[str, Any]): 发现配置
            举例：
                config = {
                    'type': 'file_watch',
                    'name': 'local_file_discovery',
                    'file_path': 'examples/discovered_servers.json',
                    'interval': 5  # 每5秒检查一次文件变化
                }
        """
        file_path = config["file_path"]
        interval = config.get("interval", 10)
        last_modified = 0

        while self.running:
            try:
                path = Path(file_path)
                if path.exists():
                    current_modified = path.stat().st_mtime
                    if current_modified > last_modified:
                        last_modified = current_modified

                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)

                        await self._process_discovery_data(data)

            except Exception as e:
                logging.error(f"文件监控发现错误: {str(e)}")

            await asyncio.sleep(interval)

    async def _multicast_discovery(self, config: Dict[str, Any]):
        """组播发现（简化实现）

        Args:
            config (Dict[str, Any]): 发现配置
            举例：
                config = {
                    'type': 'multicast',
                    'name': 'multicast_discovery',
                    'group': '239.255.0.1',
                    'port': 5000,
                    'interval': 60  # 每60秒执行一次组播发现
                }
        """
        # 这里是一个简化的组播发现实现
        # 实际应用中需要使用UDP组播
        interval = config.get("interval", 60)

        while self.running:
            try:
                # 模拟组播发现逻辑
                logging.info("执行组播服务发现...")
                # 实际实现需要UDP组播代码

            except Exception as e:
                logging.error(f"组播发现错误: {str(e)}")

            await asyncio.sleep(interval)

    async def _process_discovery_data(self, data: Dict[str, Any]):
        """处理发现的数据

        Args:
            data (Dict[str, Any]): 发现数据
        """
        try:
            servers = data.get("servers", [])

            for server_data in servers:
                registration = ServerRegistration(
                    name=server_data["name"],
                    url=server_data["url"],
                    description=server_data.get("description", ""),
                    tags=server_data.get("tags", []),
                    priority=server_data.get("priority", 0),
                    auto_connect=server_data.get("auto_connect", True),
                    health_check_url=server_data.get("health_check_url"),
                    metadata=server_data.get("metadata", {}),
                )

                self.registry.register_server(registration)
                logging.info(f"通过服务发现注册服务器: {registration.name}")

        except Exception as e:
            logging.error(f"处理发现数据失败: {str(e)}")


class DynamicMCPClient(ConfigurableMCPClient):
    """支持动态注册的MCP客户端"""

    def __init__(
        self,
        config_file: Optional[str] = None,
        registry_file: Optional[str] = None,
        api_key: str = None,
        base_url: str = None,
    ):
        super().__init__(config_file, api_key, base_url)

        # 初始化服务注册中心
        self.registry = ServiceRegistry(registry_file)
        self.discovery = ServiceDiscovery(self.registry)

        # 健康检查任务
        self.health_check_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None

        # 设置回调
        self.registry.add_callback("register", self._on_server_registered)
        self.registry.add_callback("unregister", self._on_server_unregistered)
        self.registry.add_callback("update", self._on_server_updated)

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

        # 等待任务完成
        tasks = [t for t in [self.health_check_task, self.cleanup_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        logging.info("动态功能已停止")

    def register_server_manually(self, registration: ServerRegistration) -> bool:
        """手动注册服务器"""
        return self.registry.register_server(registration)

    def unregister_server_manually(self, server_name: str) -> bool:
        """手动注销服务器"""
        return self.registry.unregister_server(server_name)

    def get_registered_servers(
        self, tags: List[str] = None
    ) -> List[ServerRegistration]:
        """获取已注册的服务器"""
        return self.registry.get_servers(tags=tags)

    async def connect_registered_servers(
        self, tags: List[str] = None, auto_connect_only: bool = True
    ):
        """连接已注册的服务器"""
        servers = self.registry.get_servers(tags=tags)

        if auto_connect_only:
            servers = [s for s in servers if s.auto_connect]

        for registration in servers:
            if registration.name not in self.servers:
                self.add_server(registration.name, registration.url)

            try:
                await self.connect_server(registration.name)
                self.registry.update_last_seen(registration.name)
                logging.info(f"连接注册服务器成功: {registration.name}")
            except Exception as e:
                logging.error(f"连接注册服务器失败 {registration.name}: {str(e)}")

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"健康检查错误: {str(e)}")

    async def _perform_health_checks(self):
        """执行健康检查"""
        for name, server in self.servers.items():
            if server.is_connected:
                try:
                    # 尝试列出工具来检查连接健康状态
                    await server.get_tools()
                    self.registry.update_last_seen(name)
                except Exception as e:
                    logging.warning(f"服务器 {name} 健康检查失败: {str(e)}")
                    # 尝试重连
                    try:
                        await self.connect_server(name)
                        self.registry.update_last_seen(name)
                        logging.info(f"服务器 {name} 重连成功")
                    except Exception as reconnect_error:
                        logging.error(f"服务器 {name} 重连失败: {str(reconnect_error)}")

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(300)  # 每5分钟清理一次
                await self._cleanup_stale_servers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"清理任务错误: {str(e)}")

    async def _cleanup_stale_servers(self):
        """清理过期服务器"""
        stale_servers = self.registry.get_stale_servers(timeout=600)  # 10分钟超时

        for server_name in stale_servers:
            logging.info(f"清理过期服务器: {server_name}")
            await self.disconnect_server(server_name)
            self.remove_server(server_name)
            # 注意：这里不从注册中心移除，只是断开连接

    def _on_server_registered(self, registration: ServerRegistration):
        """服务器注册回调"""
        logging.info(f"服务器注册事件: {registration.name}")

        # 如果设置了自动连接，则尝试连接
        if registration.auto_connect:
            asyncio.create_task(self._auto_connect_server(registration))

    def _on_server_unregistered(self, registration: ServerRegistration):
        """服务器注销回调"""
        logging.info(f"服务器注销事件: {registration.name}")

        # 断开连接并移除
        asyncio.create_task(self._auto_disconnect_server(registration.name))

    def _on_server_updated(self, registration: ServerRegistration):
        """服务器更新回调"""
        logging.info(f"服务器更新事件: {registration.name}")

        # 如果URL发生变化，需要重新连接
        if registration.name in self.servers:
            current_url = self.servers[registration.name].url
            if current_url != registration.url:
                asyncio.create_task(self._reconnect_server(registration))

    async def _auto_connect_server(self, registration: ServerRegistration):
        """自动连接服务器"""
        try:
            if registration.name not in self.servers:
                self.add_server(registration.name, registration.url)

            await self.connect_server(registration.name)
            self.registry.update_last_seen(registration.name)
            logging.info(f"自动连接服务器成功: {registration.name}")
        except Exception as e:
            logging.error(f"自动连接服务器失败 {registration.name}: {str(e)}")

    async def _auto_disconnect_server(self, server_name: str):
        """自动断开服务器"""
        try:
            await self.disconnect_server(server_name)
            self.remove_server(server_name)
            logging.info(f"自动断开服务器: {server_name}")
        except Exception as e:
            logging.error(f"自动断开服务器失败 {server_name}: {str(e)}")

    async def _reconnect_server(self, registration: ServerRegistration):
        """重新连接服务器"""
        try:
            # 先断开
            await self.disconnect_server(registration.name)
            self.remove_server(registration.name)

            # 重新添加和连接
            self.add_server(registration.name, registration.url)
            await self.connect_server(registration.name)
            self.registry.update_last_seen(registration.name)

            logging.info(f"重新连接服务器成功: {registration.name}")
        except Exception as e:
            logging.error(f"重新连接服务器失败 {registration.name}: {str(e)}")

    def show_registry_status(self):
        """显示注册中心状态"""
        print("\n📋 服务注册中心状态:")
        print("-" * 60)

        registrations = list(self.registry.registrations.values())
        if not registrations:
            print("  没有注册的服务器")
            return

        # 按优先级排序
        registrations.sort(key=lambda x: x.priority, reverse=True)

        for reg in registrations:
            status = (
                "🟢 已连接"
                if reg.name in self.servers and self.servers[reg.name].is_connected
                else "🔴 未连接"
            )
            auto_connect = "🔄 自动" if reg.auto_connect else "🔧 手动"

            print(f"  • {reg.name}: {status} {auto_connect}")
            print(f"    URL: {reg.url}")
            print(f"    描述: {reg.description}")
            print(f"    标签: {', '.join(reg.tags) if reg.tags else '无'}")
            print(f"    优先级: {reg.priority}")

            # 显示最后活跃时间
            last_seen_ago = time.time() - reg.last_seen
            if last_seen_ago < 60:
                last_seen_str = f"{int(last_seen_ago)}秒前"
            elif last_seen_ago < 3600:
                last_seen_str = f"{int(last_seen_ago/60)}分钟前"
            else:
                last_seen_str = f"{int(last_seen_ago/3600)}小时前"

            print(f"    最后活跃: {last_seen_str}")
            print()

        print(f"总计: {len(registrations)} 个注册服务器")

    async def cleanup(self):
        """清理资源"""
        await self.stop_dynamic_features()
        await super().cleanup()


# 使用示例
async def dynamic_example():
    """动态注册使用示例"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # 创建动态客户端
    client = DynamicMCPClient(
        config_file="examples/servers_config.json",
        registry_file="examples/server_registry.json",
    )

    try:
        # 手动注册一些服务器
        client.register_server_manually(
            ServerRegistration(
                name="dynamic_weather",
                url="http://localhost:9001",
                description="动态注册的天气服务",
                tags=["weather", "api"],
                priority=10,
                auto_connect=True,
            )
        )

        client.register_server_manually(
            ServerRegistration(
                name="dynamic_calculator",
                url="http://localhost:9002",
                description="动态注册的计算服务",
                tags=["math", "calculator"],
                priority=5,
                auto_connect=False,  # 手动连接
            )
        )

        # 配置服务发现
        discovery_configs = [
            {
                "type": "file_watch",
                "name": "local_discovery",
                "file_path": "examples/discovered_servers.json",
                "interval": 5,
            }
        ]

        # 启动动态功能
        await client.start_dynamic_features(discovery_configs)

        # 连接已注册的服务器
        await client.connect_registered_servers()

        # 显示状态
        client.show_registry_status()
        client.show_status()

        # 模拟运行一段时间
        print("\n🔄 动态客户端运行中，监控服务发现和健康检查...")
        print("按 Ctrl+C 退出")

        # 开始交互式聊天
        await client.chat_loop()

    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(dynamic_example())
