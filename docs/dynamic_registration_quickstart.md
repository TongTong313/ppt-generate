# MCP 服务器动态注册快速入门指南

## 概述

动态注册功能允许 MCP 客户端在运行时自动发现、注册和管理服务器，无需手动配置。这大大提高了系统的灵活性和可扩展性。

## 核心特性

### 🔄 动态服务发现
- **文件监控**: 监控配置文件变化，自动发现新服务器
- **HTTP 轮询**: 定期从发现服务器获取服务器列表
- **组播发现**: 通过网络广播自动发现服务器（未来支持）

### 📋 服务注册中心
- **集中管理**: 统一管理所有已注册的服务器
- **持久化**: 自动保存注册信息到文件
- **状态跟踪**: 实时跟踪服务器状态和健康状况

### 🏥 健康检查
- **自动检测**: 定期检查服务器健康状态
- **故障恢复**: 自动重连失效的服务器
- **状态通知**: 实时更新服务器状态

### 🏷️ 标签和优先级
- **标签分类**: 使用标签对服务器进行分类管理
- **优先级排序**: 根据优先级决定连接顺序
- **智能路由**: 基于标签和优先级进行工具路由

## 快速开始

### 1. 基础使用

```python
from ppt_generate.dynamic_mcp_client import DynamicMCPClient, ServerRegistration

# 创建动态客户端
client = DynamicMCPClient()

# 手动注册服务器
server = ServerRegistration(
    name="weather_service",
    url="http://localhost:8001",
    description="天气查询服务",
    tags=["weather", "api"],
    priority=10,
    auto_connect=True
)

client.register_server_manually(server)

# 连接服务器
await client.connect_registered_servers()

# 使用服务器
response = await client.query("今天天气怎么样？")
print(response)
```

### 2. 文件监控发现

```python
# 配置文件监控
discovery_configs = [{
    'type': 'file_watch',
    'name': 'local_discovery',
    'file_path': 'discovered_servers.json',
    'interval': 5  # 每5秒检查一次
}]

# 启动动态功能
await client.start_dynamic_features(discovery_configs)

# 客户端会自动监控文件变化并注册新服务器
```

### 3. HTTP API 发现

```python
# 配置HTTP轮询
discovery_configs = [{
    'type': 'http_polling',
    'name': 'discovery_server',
    'url': 'http://localhost:8080/api/discover',
    'interval': 15  # 每15秒轮询一次
}]

# 启动动态功能
await client.start_dynamic_features(discovery_configs)

# 客户端会定期从发现服务器获取最新的服务器列表
```

## 配置文件格式

### 服务发现配置文件 (discovered_servers.json)

```json
{
  "servers": [
    {
      "name": "weather_service",
      "url": "http://localhost:8001",
      "description": "天气查询服务",
      "tags": ["weather", "api", "external"],
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

## 运行示例

### 1. 运行完整示例

```bash
# 进入项目目录
cd d:/code/ppt-generate

# 运行动态注册示例
python examples/dynamic_registration_example.py
```

### 2. 启动发现服务器（用于HTTP发现）

```bash
# 在另一个终端运行
python examples/discovery_server.py
```

### 3. 修改发现文件（用于文件监控）

编辑 `examples/discovered_servers.json` 文件，添加或修改服务器配置，客户端会自动检测变化。

## 核心类说明

### DynamicMCPClient

主要的动态客户端类，继承自 `ConfigurableMCPClient`。

**主要方法：**
- `register_server_manually(server)`: 手动注册服务器
- `unregister_server_manually(name)`: 手动注销服务器
- `start_dynamic_features(configs)`: 启动动态发现功能
- `get_registered_servers(tags=None)`: 获取已注册的服务器
- `show_registry_status()`: 显示注册状态

### ServerRegistration

服务器注册信息的数据类。

**主要属性：**
- `name`: 服务器名称（唯一标识）
- `url`: 服务器URL
- `description`: 服务器描述
- `tags`: 标签列表
- `priority`: 优先级（数字越大优先级越高）
- `auto_connect`: 是否自动连接
- `health_check_url`: 健康检查URL
- `metadata`: 额外的元数据

### ServiceRegistry

服务注册中心，管理所有已注册的服务器。

**主要功能：**
- 服务器注册和注销
- 状态跟踪和更新
- 持久化存储
- 查询和过滤

### ServiceDiscovery

服务发现引擎，支持多种发现机制。

**支持的发现类型：**
- `file_watch`: 文件监控
- `http_polling`: HTTP轮询
- `multicast`: 组播发现（计划中）

## 最佳实践

### 1. 服务器命名

```python
# 好的命名方式
"weather_api_v1"
"user_auth_service"
"data_processor_gpu"

# 避免的命名方式
"server1"
"api"
"service"
```

### 2. 标签使用

```python
# 推荐的标签分类
tags = [
    "weather",      # 功能类型
    "api",          # 接口类型
    "external",     # 部署位置
    "v1.0",         # 版本
    "production"    # 环境
]
```

### 3. 优先级设置

```python
# 推荐的优先级范围
CRITICAL_PRIORITY = 20    # 关键服务（认证、日志）
HIGH_PRIORITY = 15        # 重要服务（AI、数据库）
NORMAL_PRIORITY = 10      # 普通服务（API、工具）
LOW_PRIORITY = 5          # 可选服务（缓存、监控）
TEST_PRIORITY = 1         # 测试服务
```

### 4. 健康检查

```python
# 为每个服务器配置健康检查
server = ServerRegistration(
    name="api_service",
    url="http://localhost:8001",
    health_check_url="http://localhost:8001/health",  # 重要！
    # ...
)
```

### 5. 错误处理

```python
try:
    await client.start_dynamic_features(discovery_configs)
except Exception as e:
    logger.error(f"启动动态功能失败: {e}")
    # 降级到静态配置
    await client.load_from_config("fallback_config.json")
```

## 故障排除

### 常见问题

1. **服务器注册失败**
   - 检查服务器名称是否唯一
   - 验证URL格式是否正确
   - 确认网络连接正常

2. **文件监控不工作**
   - 检查文件路径是否正确
   - 确认文件权限
   - 验证JSON格式

3. **HTTP发现失败**
   - 确认发现服务器正在运行
   - 检查URL和端口
   - 验证网络连接

4. **健康检查失败**
   - 检查健康检查URL
   - 确认服务器响应格式
   - 调整检查间隔

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 显示详细状态
client.show_registry_status()
client.show_status()

# 检查特定服务器
server_info = client.get_server_info("server_name")
print(f"服务器状态: {server_info}")
```

## 性能优化

### 1. 发现间隔调优

```python
# 根据需求调整发现间隔
discovery_configs = [
    {
        'type': 'file_watch',
        'interval': 5,      # 开发环境：频繁检查
    },
    {
        'type': 'http_polling',
        'interval': 60,     # 生产环境：较长间隔
    }
]
```

### 2. 连接池管理

```python
# 限制并发连接数
client = DynamicMCPClient(
    max_concurrent_connections=10,
    connection_timeout=30
)
```

### 3. 缓存策略

```python
# 启用工具缓存
client = DynamicMCPClient(
    enable_tool_cache=True,
    cache_ttl=300  # 5分钟缓存
)
```

## 扩展开发

### 自定义发现机制

```python
class CustomDiscovery:
    async def discover_servers(self):
        # 实现自定义发现逻辑
        servers = await self.fetch_from_custom_source()
        return servers

# 注册自定义发现
client.register_discovery_method('custom', CustomDiscovery())
```

### 自定义健康检查

```python
class CustomHealthChecker:
    async def check_health(self, server):
        # 实现自定义健康检查
        return await self.custom_health_check(server)

# 使用自定义健康检查
client.set_health_checker(CustomHealthChecker())
```

## 总结

动态注册功能为 MCP 客户端提供了强大的服务发现和管理能力：

- ✅ **自动化**: 减少手动配置，提高效率
- ✅ **灵活性**: 支持多种发现机制
- ✅ **可靠性**: 内置健康检查和故障恢复
- ✅ **可扩展**: 支持自定义发现和检查逻辑
- ✅ **易用性**: 简单的API和丰富的示例

通过动态注册，你可以构建更加灵活、可扩展和自动化的 MCP 服务架构。