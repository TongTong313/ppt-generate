# MCP 服务器动态注册解决方案

## 🚀 项目概述

这是一个完整的 MCP (Model Context Protocol) 服务器动态注册解决方案，提供了从基础的单服务器连接到高级的动态服务发现的完整功能集。

### 核心特性

- 🔄 **动态服务发现**: 支持文件监控、HTTP轮询等多种发现机制
- 📋 **服务注册中心**: 集中管理所有MCP服务器
- 🏥 **健康检查**: 自动监控服务器状态，支持故障恢复
- 🏷️ **标签和优先级**: 智能的服务器分类和路由
- ⚙️ **配置文件支持**: 灵活的JSON配置管理
- 🎮 **交互式界面**: 友好的命令行交互体验
- 🔧 **可扩展架构**: 支持自定义发现机制和健康检查

## 📁 项目结构

```
ppt-generate/
├── src/ppt_generate/
│   ├── mcp_client.py                    # 原始单服务器客户端
│   ├── multi_mcp_client.py              # 多服务器客户端
│   ├── config_multi_mcp_client.py       # 配置文件支持的客户端
│   └── dynamic_mcp_client.py            # 动态注册客户端 ⭐
├── examples/
│   ├── multi_server_example.py          # 多服务器使用示例
│   ├── dynamic_registration_example.py  # 动态注册完整示例 ⭐
│   ├── discovery_server.py              # HTTP发现服务器
│   ├── servers_config.json              # 服务器配置模板
│   └── discovered_servers.json          # 服务发现配置模板
├── docs/
│   ├── multi_server_mcp_guide.md        # 多服务器使用指南
│   └── dynamic_registration_quickstart.md # 动态注册快速入门 ⭐
└── README_DYNAMIC_MCP.md                 # 本文件
```

## 🎯 功能演进路径

### 1. 单服务器客户端 (`mcp_client.py`)
```python
# 基础用法
client = MCPClient()
await client.connect("http://localhost:8000")
response = await client.query("Hello")
```

### 2. 多服务器客户端 (`multi_mcp_client.py`)
```python
# 多服务器支持
client = MultiMCPClient()
await client.connect_server("weather", "http://localhost:8001")
await client.connect_server("database", "http://localhost:8002")
response = await client.query("今天天气怎么样？")
```

### 3. 配置文件客户端 (`config_multi_mcp_client.py`)
```python
# 配置文件管理
client = ConfigurableMCPClient()
await client.load_from_config("servers_config.json")
response = await client.query("查询数据库")
```

### 4. 动态注册客户端 (`dynamic_mcp_client.py`) ⭐
```python
# 动态服务发现
client = DynamicMCPClient()

# 手动注册
server = ServerRegistration(name="api", url="http://localhost:8001")
client.register_server_manually(server)

# 自动发现
discovery_configs = [{
    'type': 'file_watch',
    'file_path': 'discovered_servers.json'
}]
await client.start_dynamic_features(discovery_configs)

# 智能路由
response = await client.query("处理图像")
```

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install aiohttp asyncio pathlib watchdog
```

### 2. 基础使用

```python
from ppt_generate.dynamic_mcp_client import DynamicMCPClient, ServerRegistration

# 创建客户端
client = DynamicMCPClient()

# 注册服务器
server = ServerRegistration(
    name="weather_service",
    url="http://localhost:8001",
    description="天气查询服务",
    tags=["weather", "api"],
    priority=10
)
client.register_server_manually(server)

# 连接并使用
await client.connect_registered_servers()
response = await client.query("今天天气怎么样？")
print(response)
```

### 3. 运行示例

```bash
# 运行完整示例
python examples/dynamic_registration_example.py

# 启动HTTP发现服务器（可选）
python examples/discovery_server.py
```

## 📋 核心组件

### DynamicMCPClient

主要的动态客户端类，提供完整的动态注册功能。

**核心方法：**
- `register_server_manually(server)`: 手动注册服务器
- `unregister_server_manually(name)`: 注销服务器
- `start_dynamic_features(configs)`: 启动动态发现
- `get_registered_servers(tags=None)`: 获取服务器列表
- `show_registry_status()`: 显示注册状态
- `chat_loop()`: 交互式聊天界面

### ServerRegistration

服务器注册信息的数据结构。

```python
ServerRegistration(
    name="service_name",           # 唯一标识
    url="http://localhost:8001",   # 服务器URL
    description="服务描述",         # 描述信息
    tags=["api", "weather"],      # 标签分类
    priority=10,                   # 优先级（越大越高）
    auto_connect=True,             # 是否自动连接
    health_check_url=".../health", # 健康检查URL
    metadata={"version": "1.0"}    # 额外元数据
)
```

### ServiceRegistry

服务注册中心，管理所有已注册的服务器。

**功能：**
- 服务器注册和注销
- 状态跟踪和更新
- 持久化存储
- 查询和过滤

### ServiceDiscovery

服务发现引擎，支持多种发现机制。

**支持的发现类型：**
- `file_watch`: 文件监控发现
- `http_polling`: HTTP轮询发现
- `multicast`: 组播发现（计划中）

## 🔧 配置说明

### 服务器配置文件 (servers_config.json)

```json
{
  "servers": [
    {
      "name": "weather_api",
      "url": "http://localhost:8001",
      "description": "天气查询API",
      "enabled": true,
      "retry_count": 3,
      "timeout": 30
    }
  ],
  "client_config": {
    "max_concurrent_connections": 5,
    "default_timeout": 30,
    "retry_delay": 1
  },
  "llm_config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

### 服务发现配置文件 (discovered_servers.json)

```json
{
  "servers": [
    {
      "name": "weather_service",
      "url": "http://localhost:8001",
      "description": "天气查询服务",
      "tags": ["weather", "api"],
      "priority": 10,
      "auto_connect": true,
      "health_check_url": "http://localhost:8001/health",
      "metadata": {
        "version": "1.0.0",
        "provider": "WeatherAPI"
      }
    }
  ],
  "discovery_metadata": {
    "last_updated": "2024-01-15T10:30:00Z",
    "source": "file_discovery",
    "version": "1.0"
  }
}
```

## 🎮 使用示例

### 1. 手动注册示例

```python
async def manual_registration_example():
    client = DynamicMCPClient()
    
    # 注册多个服务器
    servers = [
        ServerRegistration(
            name="weather", url="http://localhost:8001",
            tags=["weather", "api"], priority=10
        ),
        ServerRegistration(
            name="database", url="http://localhost:8002",
            tags=["database", "storage"], priority=8
        )
    ]
    
    for server in servers:
        client.register_server_manually(server)
    
    await client.connect_registered_servers()
    
    # 使用服务器
    response = await client.query("今天天气怎么样？")
    print(response)
    
    await client.cleanup()
```

### 2. 文件监控发现示例

```python
async def file_discovery_example():
    client = DynamicMCPClient()
    
    # 配置文件监控
    discovery_configs = [{
        'type': 'file_watch',
        'name': 'local_discovery',
        'file_path': 'discovered_servers.json',
        'interval': 5
    }]
    
    # 启动动态功能
    await client.start_dynamic_features(discovery_configs)
    
    # 客户端会自动监控文件变化
    print("文件监控已启动，修改 discovered_servers.json 来添加服务器")
    
    # 等待发现
    await asyncio.sleep(10)
    
    # 连接发现的服务器
    await client.connect_registered_servers()
    
    client.show_status()
    await client.cleanup()
```

### 3. HTTP发现示例

```python
async def http_discovery_example():
    client = DynamicMCPClient()
    
    # 配置HTTP轮询
    discovery_configs = [{
        'type': 'http_polling',
        'name': 'discovery_server',
        'url': 'http://localhost:8080/api/discover',
        'interval': 15
    }]
    
    # 启动动态功能
    await client.start_dynamic_features(discovery_configs)
    
    # 等待发现
    await asyncio.sleep(20)
    
    # 连接发现的服务器
    await client.connect_registered_servers()
    
    client.show_status()
    await client.cleanup()
```

### 4. 交互式使用

```python
async def interactive_example():
    client = DynamicMCPClient()
    
    # 预注册一些服务器
    # ...
    
    # 启动交互式聊天
    await client.chat_loop()
```

## 🔍 监控和调试

### 状态查看

```python
# 显示注册状态
client.show_registry_status()

# 显示连接状态
client.show_status()

# 显示配置信息
client.show_config()

# 获取特定服务器信息
servers = client.get_registered_servers(tags=["weather"])
print(f"天气服务器: {[s.name for s in servers]}")
```

### 日志配置

```python
import logging

# 启用详细日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 或者只启用特定模块的日志
logger = logging.getLogger('ppt_generate.dynamic_mcp_client')
logger.setLevel(logging.INFO)
```

## 🛠️ 高级功能

### 1. 自定义发现机制

```python
class CustomDiscovery:
    async def discover_servers(self):
        # 实现自定义发现逻辑
        servers = await self.fetch_from_database()
        return [ServerRegistration(**server) for server in servers]

# 注册自定义发现
client.register_discovery_method('database', CustomDiscovery())
```

### 2. 自定义健康检查

```python
class CustomHealthChecker:
    async def check_health(self, server):
        # 实现自定义健康检查
        try:
            response = await self.custom_ping(server.url)
            return response.status == 200
        except:
            return False

# 使用自定义健康检查
client.set_health_checker(CustomHealthChecker())
```

### 3. 事件监听

```python
# 监听服务器状态变化
@client.on_server_status_change
async def on_status_change(server_name, old_status, new_status):
    print(f"服务器 {server_name} 状态从 {old_status} 变为 {new_status}")

# 监听新服务器发现
@client.on_server_discovered
async def on_server_discovered(server):
    print(f"发现新服务器: {server.name}")
```

## 📊 性能优化

### 1. 连接池管理

```python
client = DynamicMCPClient(
    max_concurrent_connections=10,
    connection_timeout=30,
    connection_pool_size=20
)
```

### 2. 缓存配置

```python
client = DynamicMCPClient(
    enable_tool_cache=True,
    cache_ttl=300,  # 5分钟缓存
    max_cache_size=1000
)
```

### 3. 发现间隔优化

```python
# 开发环境：频繁检查
discovery_configs = [{
    'type': 'file_watch',
    'interval': 2
}]

# 生产环境：较长间隔
discovery_configs = [{
    'type': 'http_polling',
    'interval': 60
}]
```

## 🚨 故障排除

### 常见问题

1. **服务器注册失败**
   ```python
   # 检查服务器名称唯一性
   existing = client.get_registered_servers()
   names = [s.name for s in existing]
   print(f"已注册的服务器: {names}")
   ```

2. **文件监控不工作**
   ```python
   # 检查文件路径和权限
   import os
   file_path = "discovered_servers.json"
   print(f"文件存在: {os.path.exists(file_path)}")
   print(f"文件可读: {os.access(file_path, os.R_OK)}")
   ```

3. **HTTP发现失败**
   ```python
   # 测试发现服务器连接
   import aiohttp
   async with aiohttp.ClientSession() as session:
       async with session.get('http://localhost:8080/api/discover') as resp:
           print(f"状态码: {resp.status}")
           print(f"响应: {await resp.text()}")
   ```

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 检查内部状态
print(f"注册中心状态: {client.registry.get_all_servers()}")
print(f"连接状态: {client.get_connection_status()}")
print(f"发现状态: {client.get_discovery_status()}")

# 手动触发健康检查
await client.perform_health_check()
```

## 🔮 未来计划

- [ ] **组播发现**: 支持UDP组播自动发现
- [ ] **负载均衡**: 智能的请求分发和负载均衡
- [ ] **服务网格**: 与Istio等服务网格集成
- [ ] **监控集成**: 与Prometheus、Grafana集成
- [ ] **安全增强**: 支持TLS、认证和授权
- [ ] **插件系统**: 可扩展的插件架构
- [ ] **Web界面**: 图形化的管理界面
- [ ] **集群支持**: 多节点集群部署

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如果你有任何问题或建议，请：

- 创建 [Issue](https://github.com/your-repo/issues)
- 发送邮件到 your-email@example.com
- 加入我们的 [Discord](https://discord.gg/your-server)

---

**🎉 感谢使用 MCP 动态注册解决方案！**

这个解决方案为你提供了从简单的单服务器连接到复杂的动态服务发现的完整功能。无论你是在开发原型还是部署生产系统，都能找到适合的解决方案。

开始你的 MCP 动态注册之旅吧！ 🚀