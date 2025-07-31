# MCP动态注册客户端

基于真正MCP协议的动态服务器注册和发现解决方案，完全集成了MCP工具的特性。

## 🚀 核心特性

### 1. 真正的MCP协议集成
- **继承自MultiMCPClient**: 完全兼容现有的`mcp_client.py`架构
- **工具发现**: 自动发现所有已连接服务器的MCP工具
- **工具调用**: 支持通过自然语言查询调用MCP工具
- **协议标准**: 严格遵循MCP协议规范

### 2. 动态服务注册
- **服务注册中心**: `MCPServiceRegistry`管理所有MCP服务器
- **自动连接**: 支持服务器注册时自动连接
- **状态管理**: 实时跟踪服务器健康状态
- **持久化**: 注册信息自动保存到文件

### 3. 智能服务发现
- **文件监控**: 监控配置文件变化，自动发现新服务器
- **HTTP轮询**: 定期从HTTP端点获取服务器列表
- **MCP广播**: 基于MCP协议的服务发现机制
- **多源发现**: 支持同时使用多种发现方式

### 4. 健康监控
- **自动健康检查**: 定期检查服务器健康状态
- **连接管理**: 自动重连失败的服务器
- **状态回调**: 服务器状态变化时触发回调
- **清理机制**: 自动清理长时间无响应的服务器

### 5. 增强的工具管理
- **工具发现工具**: 内置服务发现和管理工具
- **统一工具接口**: 将MCP工具和管理工具统一呈现
- **智能路由**: 自动找到工具对应的服务器
- **错误处理**: 完善的工具调用错误处理机制

## 📁 文件结构

```
src/ppt_generate/
├── mcp_dynamic_client.py      # 主要的动态客户端实现
├── mcp_dynamic_example.py     # 使用示例和演示
├── discovered_servers.json    # 服务发现配置文件
├── README_MCP_DYNAMIC.md      # 本文档
└── mcp_registry.json         # 服务注册信息（运行时生成）
```

## 🔧 核心组件

### MCPServerRegistration
服务器注册信息数据类：
```python
@dataclass
class MCPServerRegistration:
    name: str                    # 服务器名称
    url: str                     # 服务器URL
    description: str = ""        # 描述信息
    tags: List[str] = None       # 标签列表
    priority: int = 10           # 优先级
    auto_connect: bool = True    # 是否自动连接
    health_check_url: str = None # 健康检查URL
    metadata: Dict = None        # 元数据
    status: str = "unknown"      # 当前状态
```

### MCPServiceRegistry
服务注册中心，管理所有MCP服务器：
- `register_server()`: 注册新服务器
- `unregister_server()`: 注销服务器
- `get_servers_by_tags()`: 按标签查找服务器
- `update_server_status()`: 更新服务器状态

### MCPServiceDiscovery
服务发现引擎，支持多种发现方式：
- `_file_watch_discovery()`: 文件监控发现
- `_http_polling_discovery()`: HTTP轮询发现
- `_mcp_broadcast_discovery()`: MCP广播发现

### MCPDynamicClient
主要的动态客户端类，继承自`MultiMCPClient`：
- `discover_and_call_tools()`: 发现工具并处理查询
- `connect_registered_servers()`: 连接已注册的服务器
- `start_dynamic_features()`: 启动动态功能
- `chat_loop()`: 交互式聊天循环

## 🛠️ 使用方法

### 1. 基本使用

```python
from mcp_dynamic_client import MCPDynamicClient, MCPServerRegistration

# 创建客户端
client = MCPDynamicClient(
    registry_file="mcp_registry.json",
    api_key="your-api-key"
)

# 注册服务器
weather_server = MCPServerRegistration(
    name="weather",
    url="http://localhost:8001",
    description="天气查询服务",
    tags=["weather", "api"],
    auto_connect=True
)

client.register_server_manually(weather_server)

# 启动动态功能
discovery_configs = [
    {
        "type": "file_watch",
        "file_path": "discovered_servers.json",
        "interval": 10
    }
]

await client.start_dynamic_features(discovery_configs)
await client.connect_registered_servers()

# 使用工具
response = await client.discover_and_call_tools("今天北京的天气怎么样？")
print(response)
```

### 2. 服务发现配置

创建`discovered_servers.json`文件：
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
      "health_check_url": "http://localhost:8001/health"
    }
  ]
}
```

### 3. 交互模式

```python
# 启动交互式聊天
await client.chat_loop()
```

支持的命令：
- `status`: 查看服务器连接状态
- `registry`: 查看注册状态
- `tools`: 查看可用工具
- `discover`: 手动发现服务器
- `quit`/`再见`: 退出

## 🔍 内置工具

动态客户端提供了以下内置管理工具：

### 1. discover_mcp_servers
发现可用的MCP服务器
```python
# 发现所有服务器
result = await client._handle_discovery_tool("discover_mcp_servers", {})

# 按标签发现
result = await client._handle_discovery_tool(
    "discover_mcp_servers", 
    {"tags": ["weather"]}
)
```

### 2. get_server_status
获取服务器状态信息
```python
# 获取所有服务器状态
result = await client._handle_discovery_tool("get_server_status", {})

# 获取特定服务器状态
result = await client._handle_discovery_tool(
    "get_server_status", 
    {"server_name": "weather"}
)
```

### 3. connect_mcp_server
连接到指定的MCP服务器
```python
result = await client._handle_discovery_tool(
    "connect_mcp_server", 
    {"server_name": "weather"}
)
```

## 🔄 与原有代码的对比

### 原有`dynamic_mcp_client.py`的问题：
1. **不基于MCP协议**: 没有真正使用MCP的工具发现和调用机制
2. **缺少工具集成**: 无法发现和调用MCP服务器提供的工具
3. **简单的连接管理**: 只是简单的HTTP连接，没有MCP协议握手
4. **有限的功能**: 主要是服务注册，缺少实际的MCP功能

### 新`mcp_dynamic_client.py`的改进：
1. **真正的MCP集成**: 继承自`MultiMCPClient`，完全兼容MCP协议
2. **完整的工具生态**: 自动发现、调用和管理MCP工具
3. **智能查询处理**: 使用LLM智能选择和调用合适的工具
4. **增强的管理功能**: 内置服务发现、状态监控、连接管理工具
5. **更好的用户体验**: 支持自然语言查询和交互式操作

## 🚦 运行示例

### 1. 运行演示程序
```bash
python mcp_dynamic_example.py
```

### 2. 选择演示模式
- **基本使用演示**: 展示核心功能
- **交互模式演示**: 体验聊天界面
- **服务发现演示**: 观察自动发现过程
- **健康监控演示**: 查看健康检查机制

## 📋 配置说明

### 服务发现配置
```python
discovery_configs = [
    {
        "type": "file_watch",        # 发现类型
        "file_path": "servers.json", # 监控文件路径
        "interval": 10               # 检查间隔（秒）
    },
    {
        "type": "http_polling",      # HTTP轮询
        "url": "http://localhost:9000/api/servers",
        "interval": 30               # 轮询间隔（秒）
    }
]
```

### 服务器注册配置
```python
server = MCPServerRegistration(
    name="service_name",           # 唯一服务名
    url="http://localhost:8001",   # MCP服务器URL
    description="服务描述",        # 可选描述
    tags=["tag1", "tag2"],        # 标签列表
    priority=10,                   # 优先级（数字越大越优先）
    auto_connect=True,             # 是否自动连接
    health_check_url="http://...", # 健康检查URL（可选）
    metadata={"key": "value"}     # 自定义元数据
)
```

## 🔧 扩展开发

### 1. 添加新的发现方式
```python
async def _custom_discovery(self, config: Dict[str, Any]):
    """自定义发现方式"""
    while self.running:
        # 实现你的发现逻辑
        await self._process_discovery_data(discovered_data)
        await asyncio.sleep(config.get("interval", 60))
```

### 2. 添加自定义回调
```python
def my_callback(registration: MCPServerRegistration):
    print(f"服务器 {registration.name} 状态变化")

client.registry.add_callback("status_change", my_callback)
```

### 3. 扩展内置工具
```python
def _create_custom_tools(self) -> List[Dict[str, Any]]:
    """创建自定义管理工具"""
    return [
        {
            "type": "function",
            "function": {
                "name": "custom_tool",
                "description": "自定义工具描述",
                "parameters": {...}
            }
        }
    ]
```

## 🐛 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查服务器URL是否正确
   - 确认服务器是否运行
   - 查看日志中的错误信息

2. **工具调用失败**
   - 确认服务器已连接
   - 检查工具参数是否正确
   - 查看MCP协议握手是否成功

3. **服务发现不工作**
   - 检查发现配置文件路径
   - 确认文件格式正确
   - 查看发现任务是否启动

### 调试技巧

1. **启用详细日志**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. **查看注册状态**
```python
client.show_registry_status()
client.show_status()
```

3. **手动测试连接**
```python
await client.connect_server("server_name")
tools = await client.servers["server_name"].get_tools()
```

## 📈 性能优化

1. **合理设置检查间隔**: 避免过于频繁的健康检查
2. **使用标签过滤**: 减少不必要的服务器连接
3. **优化工具调用**: 缓存工具列表，减少重复获取
4. **异步处理**: 充分利用异步特性，避免阻塞

## 🔮 未来计划

1. **负载均衡**: 支持多个相同服务的负载均衡
2. **服务网格**: 实现服务间的自动发现和通信
3. **监控面板**: 提供Web界面监控服务状态
4. **插件系统**: 支持第三方插件扩展功能
5. **集群支持**: 支持分布式部署和管理

---

**注意**: 这个实现完全基于MCP协议，与现有的`mcp_client.py`和`mcp_server.py`完全兼容，提供了真正的MCP工具集成和动态管理功能。