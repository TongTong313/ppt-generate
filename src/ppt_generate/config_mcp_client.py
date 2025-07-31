import json
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass
from mcp_client import MultiMCPClient, ServerConnection


@dataclass
class ServerConfig:
    """服务器配置数据类"""

    name: str
    url: str
    description: str = ""
    enabled: bool = True
    retry_attempts: int = 3
    timeout: int = 30


@dataclass
class ClientSettings:
    """客户端设置数据类"""

    max_concurrent_connections: int = 5
    connection_timeout: int = 30
    retry_delay: int = 2
    health_check_interval: int = 60


@dataclass
class LLMSettings:
    """LLM设置数据类"""

    model: str = "qwen-plus"
    max_tokens: int = 1000
    temperature: float = 0.7


class ConfigurableMCPClient(MultiMCPClient):
    """支持配置文件的多服务器MCP客户端"""

    def __init__(
        self,
        config_file: Optional[str] = None,
        api_key: str = None,
        base_url: str = None,
    ):
        # 默认配置
        self.server_configs: List[ServerConfig] = []
        self.client_settings = ClientSettings()
        self.llm_settings = LLMSettings()

        # 如果提供了配置文件，加载配置
        if config_file:
            self.load_config(config_file)

        # 初始化父类
        super().__init__(
            api_key=api_key or self._get_api_key(),
            base_url=base_url or self._get_base_url(),
        )

        # 根据配置添加服务器
        self._setup_servers_from_config()

    def _get_api_key(self) -> str:
        """获取API密钥"""
        import os

        return os.getenv("DASHSCOPE_API_KEY", "")

    def _get_base_url(self) -> str:
        """获取基础URL"""
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def load_config(self, config_file: str):
        """从JSON文件加载配置"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                raise FileNotFoundError(f"配置文件不存在: {config_file}")

            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # 解析服务器配置
            self.server_configs = []
            for server_data in config_data.get("servers", []):
                server_config = ServerConfig(
                    name=server_data["name"],
                    url=server_data["url"],
                    description=server_data.get("description", ""),
                    enabled=server_data.get("enabled", True),
                    retry_attempts=server_data.get("retry_attempts", 3),
                    timeout=server_data.get("timeout", 30),
                )
                self.server_configs.append(server_config)

            # 解析客户端设置
            client_data = config_data.get("client_settings", {})
            self.client_settings = ClientSettings(
                max_concurrent_connections=client_data.get(
                    "max_concurrent_connections", 5
                ),
                connection_timeout=client_data.get("connection_timeout", 30),
                retry_delay=client_data.get("retry_delay", 2),
                health_check_interval=client_data.get("health_check_interval", 60),
            )

            # 解析LLM设置
            llm_data = config_data.get("llm_settings", {})
            self.llm_settings = LLMSettings(
                model=llm_data.get("model", "qwen-plus"),
                max_tokens=llm_data.get("max_tokens", 1000),
                temperature=llm_data.get("temperature", 0.7),
            )

            print(f"✅ 成功加载配置文件: {config_file}")
            print(f"   - 服务器数量: {len(self.server_configs)}")
            print(
                f"   - 启用的服务器: {sum(1 for s in self.server_configs if s.enabled)}"
            )

        except Exception as e:
            print(f"❌ 加载配置文件失败: {str(e)}")
            raise

    def save_config(self, config_file: str):
        """保存当前配置到JSON文件"""
        try:
            config_data = {
                "servers": [
                    {
                        "name": server.name,
                        "url": server.url,
                        "description": server.description,
                        "enabled": server.enabled,
                        "retry_attempts": server.retry_attempts,
                        "timeout": server.timeout,
                    }
                    for server in self.server_configs
                ],
                "client_settings": {
                    "max_concurrent_connections": self.client_settings.max_concurrent_connections,
                    "connection_timeout": self.client_settings.connection_timeout,
                    "retry_delay": self.client_settings.retry_delay,
                    "health_check_interval": self.client_settings.health_check_interval,
                },
                "llm_settings": {
                    "model": self.llm_settings.model,
                    "max_tokens": self.llm_settings.max_tokens,
                    "temperature": self.llm_settings.temperature,
                },
            }

            config_path = Path(config_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            print(f"✅ 配置已保存到: {config_file}")

        except Exception as e:
            print(f"❌ 保存配置文件失败: {str(e)}")
            raise

    def _setup_servers_from_config(self):
        """根据配置设置服务器"""
        for server_config in self.server_configs:
            if server_config.enabled:
                self.add_server(server_config.name, server_config.url)
                print(
                    f"📝 从配置添加服务器: {server_config.name} - {server_config.description}"
                )

    async def connect_enabled_servers(self):
        """只连接配置中启用的服务器"""
        enabled_servers = [s for s in self.server_configs if s.enabled]

        if not enabled_servers:
            print("⚠️ 没有启用的服务器")
            return

        print(f"🔄 开始连接 {len(enabled_servers)} 个启用的服务器...")

        # 使用配置的超时时间和重试次数
        tasks = []
        for server_config in enabled_servers:
            if server_config.name in self.servers:
                task = self._connect_server_with_retry(
                    server_config.name,
                    server_config.retry_attempts,
                    server_config.timeout,
                )
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 统计连接结果
            connected_count = sum(
                1 for server in self.servers.values() if server.is_connected
            )
            print(
                f"📊 连接完成: {connected_count}/{len(enabled_servers)} 个服务器连接成功"
            )

    async def _connect_server_with_retry(
        self, server_name: str, retry_attempts: int, timeout: int
    ):
        """带重试机制的服务器连接"""
        for attempt in range(retry_attempts):
            try:
                # 这里可以添加超时控制
                await asyncio.wait_for(
                    self.servers[server_name].connect(), timeout=timeout
                )
                return True
            except asyncio.TimeoutError:
                print(
                    f"⏰ 服务器 {server_name} 连接超时 (尝试 {attempt + 1}/{retry_attempts})"
                )
            except Exception as e:
                print(
                    f"❌ 服务器 {server_name} 连接失败 (尝试 {attempt + 1}/{retry_attempts}): {str(e)}"
                )

            if attempt < retry_attempts - 1:
                await asyncio.sleep(self.client_settings.retry_delay)

        return False

    async def process_query(self, query: str) -> str:
        """使用配置的LLM设置处理查询"""
        messages = [{"role": "user", "content": query}]

        # 获取所有服务器的工具
        all_tools_by_server = await self.get_all_tools()

        # 合并所有工具为OpenAI格式
        available_tools = []
        for server_name, tools in all_tools_by_server.items():
            for tool in tools:
                available_tools.append(
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": f"[{server_name}] {tool.description}",
                            "parameters": tool.inputSchema,
                        },
                    }
                )

        if not available_tools:
            return "⚠️ 没有可用的工具，请确保至少有一个服务器已连接"

        print(f"🔧 可用工具数量: {len(available_tools)}")

        # 使用配置的LLM设置
        response = await self.llm.chat.completions.create(
            model=self.llm_settings.model,
            max_tokens=self.llm_settings.max_tokens,
            temperature=self.llm_settings.temperature,
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

                # 找到工具对应的服务器
                server_name = self._find_tool_server(tool_name, all_tools_by_server)

                if server_name and server_name in self.servers:
                    try:
                        result = await self.servers[server_name].call_tool(
                            tool_name, tool_args
                        )
                        print(f"✅ 工具 {tool_name} 在服务器 {server_name} 上执行成功")

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
            model=self.llm_settings.model,
            max_tokens=self.llm_settings.max_tokens,
            temperature=self.llm_settings.temperature,
            messages=messages,
            tools=available_tools,
        )

        return response.choices[0].message.content

    def show_config(self):
        """显示当前配置"""
        print("\n⚙️ 当前配置:")
        print("-" * 50)

        print(f"📡 服务器配置 ({len(self.server_configs)} 个):")
        for server in self.server_configs:
            status = "🟢 启用" if server.enabled else "🔴 禁用"
            print(f"  • {server.name}: {status}")
            print(f"    URL: {server.url}")
            print(f"    描述: {server.description}")
            print(f"    重试次数: {server.retry_attempts}, 超时: {server.timeout}s")

        print(f"\n🔧 客户端设置:")
        print(f"  • 最大并发连接: {self.client_settings.max_concurrent_connections}")
        print(f"  • 连接超时: {self.client_settings.connection_timeout}s")
        print(f"  • 重试延迟: {self.client_settings.retry_delay}s")
        print(f"  • 健康检查间隔: {self.client_settings.health_check_interval}s")

        print(f"\n🤖 LLM设置:")
        print(f"  • 模型: {self.llm_settings.model}")
        print(f"  • 最大令牌: {self.llm_settings.max_tokens}")
        print(f"  • 温度: {self.llm_settings.temperature}")

    def enable_server(self, server_name: str):
        """启用指定服务器"""
        for server in self.server_configs:
            if server.name == server_name:
                server.enabled = True
                if server_name not in self.servers:
                    self.add_server(server_name, server.url)
                print(f"✅ 已启用服务器: {server_name}")
                return
        print(f"⚠️ 找不到服务器: {server_name}")

    def disable_server(self, server_name: str):
        """禁用指定服务器"""
        for server in self.server_configs:
            if server.name == server_name:
                server.enabled = False
                if server_name in self.servers:
                    asyncio.create_task(self.disconnect_server(server_name))
                    self.remove_server(server_name)
                print(f"🔴 已禁用服务器: {server_name}")
                return
        print(f"⚠️ 找不到服务器: {server_name}")


# 使用示例
async def config_example():
    """配置文件使用示例"""
    # 从配置文件创建客户端
    client = ConfigurableMCPClient(config_file="examples/servers_config.json")

    try:
        # 显示配置
        client.show_config()

        # 连接启用的服务器
        await client.connect_enabled_servers()

        # 显示连接状态
        client.show_status()

        # 开始聊天循环
        await client.chat_loop()

    finally:
        # 清理连接
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(config_example())
