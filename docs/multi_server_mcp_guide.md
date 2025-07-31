# 多服务器MCP客户端使用指南

本指南介绍如何使用多服务器MCP客户端来同时连接和管理多个MCP服务器。

## 概述

多服务器MCP客户端允许你：
- 同时连接多个MCP服务器
- 统一管理所有服务器的工具
- 通过配置文件管理服务器设置
- 智能路由工具调用到正确的服务器
- 监控服务器连接状态

## 文件结构

```
src/ppt_generate/
├── mcp_client.py              # 原始单服务器客户端
├── multi_mcp_client.py        # 多服务器客户端
└── config_multi_mcp_client.py # 支持配置文件的多服务器客户端

examples/
├── multi_server_example.py    # 使用示例
└── servers_config.json        # 配置文件示例
```

## 快速开始

### 1. 基础使用

```python
import asyncio
from ppt_generate.multi_mcp_client import MultiMCPClient

async def main():
    # 创建客户端
    client = MultiMCPClient()
    
    # 添加多个服务器
    client.add_server("weather", "http://localhost:8001")
    client.add_server("database", "http://localhost:8002")
    client.add_server("files", "http://localhost:8003")
    
    try:
        # 连接所有服务器
        await client.connect_all_servers()
        
        # 处理查询
        response = await client.process_query("请帮我查看天气")
        print(response)
        
    finally:
        # 清理连接
        await client.cleanup()

asyncio.run(main())
```

### 2. 使用配置文件

首先创建配置文件 `servers_config.json`：

```json
{
  "servers": [
    {
      "name": "weather",
      "url": "http://localhost:8001",
      "description": "天气查询服务",
      "enabled": true,
      "retry_attempts": 3,
      "timeout": 30
    },
    {
      "name": "database",
      "url": "http://localhost:8002",
      "description": "数据库操作服务",
      "enabled": true,
      "retry_attempts": 2,
      "timeout": 60
    }
  ],
  "client_settings": {
    "max_concurrent_connections": 5,
    "connection_timeout": 30,
    "retry_delay": 2,
    "health_check_interval": 60
  },
  "llm_settings": {
    "model": "qwen-plus",
    "max_tokens": 1000,
    "temperature": 0.7
  }
}
```

然后使用配置文件：

```python
import asyncio
from ppt_generate.config_multi_mcp_client import ConfigurableMCPClient

async def main():
    # 从配置文件创建客户端
    client = ConfigurableMCPClient(config_file="servers_config.json")
    
    try:
        # 连接启用的服务器
        await client.connect_enabled_servers()
        
        # 显示配置和状态
        client.show_config()
        client.show_status()
        
        # 开始交互式聊天
        await client.chat_loop()
        
    finally:
        await client.cleanup()

asyncio.run(main())
```

## 核心功能

### 服务器管理

```python
# 添加服务器
client.add_server("server_name", "http://localhost:8001")

# 移除服务器
client.remove_server("server_name")

# 连接单个服务器
await client.connect_server("server_name")

# 断开单个服务器
await client.disconnect_server("server_name")

# 连接所有服务器
await client.connect_all_servers()

# 断开所有服务器
await client.disconnect_all_servers()
```

### 状态监控

```python
# 显示服务器连接状态
client.show_status()

# 获取已连接的服务器列表
connected_servers = client.get_connected_servers()

# 获取所有工具
all_tools = await client.get_all_tools()
```

### 配置管理（ConfigurableMCPClient）

```python
# 显示当前配置
client.show_config()

# 启用/禁用服务器
client.enable_server("server_name")
client.disable_server("server_name")

# 保存配置到文件
client.save_config("new_config.json")
```

## 交互式命令

在交互式聊天模式中，你可以使用以下特殊命令：

- `status` - 查看服务器连接状态
- `tools` - 查看所有可用工具
- `quit` 或 `再见` - 退出程序

## 工具调用机制

客户端会自动：
1. 收集所有已连接服务器的工具
2. 将工具信息提供给LLM
3. 当LLM决定调用工具时，自动路由到正确的服务器
4. 返回工具执行结果给LLM
5. 生成最终回复

## 错误处理

### 连接失败
- 自动重试机制（可配置重试次数）
- 超时控制
- 详细的错误日志

### 工具调用失败
- 优雅的错误处理
- 错误信息传递给LLM
- 继续处理其他工具调用

## 配置选项详解

### 服务器配置
- `name`: 服务器名称（唯一标识）
- `url`: 服务器URL地址
- `description`: 服务器描述
- `enabled`: 是否启用该服务器
- `retry_attempts`: 连接失败时的重试次数
- `timeout`: 连接超时时间（秒）

### 客户端设置
- `max_concurrent_connections`: 最大并发连接数
- `connection_timeout`: 连接超时时间
- `retry_delay`: 重试间隔时间
- `health_check_interval`: 健康检查间隔

### LLM设置
- `model`: 使用的模型名称
- `max_tokens`: 最大令牌数
- `temperature`: 生成温度

## 最佳实践

### 1. 服务器命名
- 使用有意义的名称，如 `weather`、`database`、`files`
- 避免使用特殊字符和空格

### 2. 错误处理
- 总是使用 try-finally 块确保资源清理
- 监控连接状态，及时重连失败的服务器

### 3. 性能优化
- 合理设置并发连接数
- 根据服务器响应时间调整超时设置
- 定期检查服务器健康状态

### 4. 配置管理
- 将服务器配置存储在版本控制中
- 为不同环境（开发、测试、生产）使用不同的配置文件
- 定期备份配置文件

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查服务器是否正在运行
   - 验证URL地址是否正确
   - 检查网络连接
   - 查看防火墙设置

2. **工具调用失败**
   - 确认工具参数格式正确
   - 检查服务器日志
   - 验证工具权限

3. **配置文件错误**
   - 验证JSON格式
   - 检查必需字段
   - 确认文件路径正确

### 调试技巧

1. **启用详细日志**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

2. **单独测试服务器连接**
   ```python
   success = await client.connect_server("server_name")
   if not success:
       print("连接失败，检查服务器状态")
   ```

3. **检查工具可用性**
   ```python
   tools = await client.get_all_tools()
   for server_name, server_tools in tools.items():
       print(f"{server_name}: {len(server_tools)} 个工具")
   ```

## 示例场景

### 场景1：多功能助手
```python
# 配置多个专业服务器
client.add_server("weather", "http://localhost:8001")      # 天气服务
client.add_server("calculator", "http://localhost:8002")   # 计算服务
client.add_server("translator", "http://localhost:8003")   # 翻译服务
client.add_server("database", "http://localhost:8004")     # 数据库服务

# 用户可以问："今天天气如何？帮我计算一下1+1，然后把结果翻译成英文"
# 客户端会自动调用相应的服务器工具
```

### 场景2：开发环境
```python
# 开发环境配置
client.add_server("dev_db", "http://localhost:8001")
client.add_server("test_api", "http://localhost:8002")
client.add_server("mock_service", "http://localhost:8003")
```

### 场景3：生产环境
```python
# 生产环境配置（使用配置文件）
client = ConfigurableMCPClient(config_file="production_config.json")
```

## 扩展开发

如果你需要扩展功能，可以继承现有类：

```python
class CustomMCPClient(ConfigurableMCPClient):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    async def custom_health_check(self):
        """自定义健康检查"""
        for name, server in self.servers.items():
            if server.is_connected:
                try:
                    # 执行健康检查逻辑
                    await server.session.list_tools()
                    print(f"✅ {name} 健康状态良好")
                except Exception as e:
                    print(f"❌ {name} 健康检查失败: {str(e)}")
                    # 可以选择重连
                    await self.connect_server(name)
```

## 总结

多服务器MCP客户端提供了强大而灵活的方式来管理多个MCP服务器。通过合理的配置和使用，你可以构建复杂的多服务协作系统，为用户提供丰富的功能体验。

记住始终遵循最佳实践，做好错误处理和资源管理，确保系统的稳定性和可靠性。