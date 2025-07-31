#!/usr/bin/env python3
"""
MCP动态注册客户端使用示例

这个示例展示了如何使用基于MCP协议的动态注册客户端，
包括服务发现、工具调用和管理功能。
"""

import asyncio
import logging
import json
from pathlib import Path
from mcp_dynamic_client import MCPDynamicClient, MCPServerRegistration


async def demo_basic_usage():
    """基本使用演示"""
    print("\n=== MCP动态客户端基本使用演示 ===")
    
    # 创建动态客户端
    client = MCPDynamicClient(
        registry_file="mcp_registry.json",
        api_key="your-api-key",  # 替换为实际的API密钥
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"  # 或其他LLM服务
    )
    
    try:
        # 1. 手动注册服务器
        print("\n1. 手动注册MCP服务器...")
        
        # 注册天气服务
        weather_server = MCPServerRegistration(
            name="weather",
            url="http://localhost:8001",
            description="天气查询和预报服务",
            tags=["weather", "forecast"],
            priority=10,
            auto_connect=True
        )
        
        # 注册文件管理服务
        file_server = MCPServerRegistration(
            name="file_manager",
            url="http://localhost:8002",
            description="文件管理和操作服务",
            tags=["file", "storage"],
            priority=8,
            auto_connect=True
        )
        
        client.register_server_manually(weather_server)
        client.register_server_manually(file_server)
        
        print("✅ 服务器注册完成")
        
        # 2. 启动动态功能
        print("\n2. 启动服务发现和健康检查...")
        
        discovery_configs = [
            {
                "type": "file_watch",
                "file_path": "discovered_servers.json",
                "interval": 10  # 每10秒检查一次文件变化
            },
            {
                "type": "http_polling",
                "url": "http://localhost:9000/api/servers",
                "interval": 30  # 每30秒轮询一次
            }
        ]
        
        await client.start_dynamic_features(discovery_configs)
        print("✅ 动态功能启动完成")
        
        # 3. 连接已注册的服务器
        print("\n3. 连接已注册的服务器...")
        await client.connect_registered_servers()
        
        # 4. 显示状态
        print("\n4. 显示当前状态:")
        client.show_registry_status()
        client.show_status()
        
        # 5. 演示工具发现和调用
        print("\n5. 演示工具发现和调用:")
        
        # 发现所有可用工具
        all_tools = await client.get_all_tools()
        print(f"发现 {sum(len(tools) for tools in all_tools.values())} 个工具")
        
        # 演示查询处理
        queries = [
            "今天北京的天气怎么样？",
            "帮我列出当前目录下的所有文件",
            "发现有哪些可用的MCP服务器？",
            "连接到weather服务器"
        ]
        
        for query in queries:
            print(f"\n🔍 查询: {query}")
            try:
                response = await client.discover_and_call_tools(query)
                print(f"🤖 回复: {response}")
            except Exception as e:
                print(f"❌ 错误: {str(e)}")
            
            await asyncio.sleep(2)  # 稍作停顿
        
        # 6. 演示服务器管理
        print("\n6. 演示服务器管理:")
        
        # 获取特定标签的服务器
        weather_servers = client.get_registered_servers(tags=["weather"])
        print(f"找到 {len(weather_servers)} 个天气相关服务器")
        
        # 手动连接服务器
        print("\n尝试手动连接服务器...")
        for server in client.get_registered_servers():
            if server.name not in client.servers:
                try:
                    client.add_server(server.name, server.url)
                    await client.connect_server(server.name)
                    print(f"✅ 成功连接: {server.name}")
                except Exception as e:
                    print(f"❌ 连接失败 {server.name}: {str(e)}")
        
        print("\n=== 演示完成 ===")
        
    except Exception as e:
        print(f"❌ 演示过程中发生错误: {str(e)}")
    
    finally:
        # 清理资源
        await client.cleanup()
        print("\n🧹 资源清理完成")


async def demo_interactive_mode():
    """交互模式演示"""
    print("\n=== MCP动态客户端交互模式演示 ===")
    
    client = MCPDynamicClient(
        registry_file="mcp_registry.json",
        api_key="your-api-key",  # 替换为实际的API密钥
    )
    
    try:
        # 预注册一些服务器
        servers = [
            MCPServerRegistration(
                name="demo_weather",
                url="http://localhost:8001",
                description="演示天气服务",
                tags=["weather", "demo"],
                auto_connect=True
            ),
            MCPServerRegistration(
                name="demo_files",
                url="http://localhost:8002",
                description="演示文件服务",
                tags=["files", "demo"],
                auto_connect=True
            )
        ]
        
        for server in servers:
            client.register_server_manually(server)
        
        # 启动动态功能
        discovery_configs = [
            {
                "type": "file_watch",
                "file_path": "discovered_servers.json",
                "interval": 5
            }
        ]
        
        await client.start_dynamic_features(discovery_configs)
        await client.connect_registered_servers()
        
        # 进入交互模式
        await client.chat_loop()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"❌ 交互模式错误: {str(e)}")
    finally:
        await client.cleanup()


async def demo_service_discovery():
    """服务发现演示"""
    print("\n=== 服务发现功能演示 ===")
    
    client = MCPDynamicClient(registry_file="mcp_registry.json")
    
    try:
        # 创建发现配置文件
        discovery_file = "discovered_servers.json"
        
        # 确保发现文件存在
        if not Path(discovery_file).exists():
            print(f"创建发现文件: {discovery_file}")
            # 文件已经在前面创建了
        
        # 启动文件监控发现
        discovery_configs = [
            {
                "type": "file_watch",
                "file_path": discovery_file,
                "interval": 3  # 每3秒检查一次
            }
        ]
        
        await client.start_dynamic_features(discovery_configs)
        
        print("\n📡 服务发现已启动，监控文件变化...")
        print(f"监控文件: {discovery_file}")
        print("\n你可以修改发现文件来添加新的服务器")
        print("按 Ctrl+C 停止监控")
        
        # 定期显示注册状态
        for i in range(20):  # 运行1分钟
            await asyncio.sleep(3)
            
            print(f"\n--- 第 {i+1} 次检查 ---")
            client.show_registry_status()
            
            # 尝试连接新发现的服务器
            await client.connect_registered_servers()
        
    except KeyboardInterrupt:
        print("\n👋 停止服务发现")
    except Exception as e:
        print(f"❌ 服务发现错误: {str(e)}")
    finally:
        await client.cleanup()


async def demo_health_monitoring():
    """健康监控演示"""
    print("\n=== 健康监控功能演示 ===")
    
    client = MCPDynamicClient(registry_file="mcp_registry.json")
    
    try:
        # 注册一些测试服务器（包括可能不存在的）
        test_servers = [
            MCPServerRegistration(
                name="healthy_server",
                url="http://localhost:8001",
                description="健康的测试服务器",
                health_check_url="http://localhost:8001/health",
                auto_connect=True
            ),
            MCPServerRegistration(
                name="unhealthy_server",
                url="http://localhost:9999",  # 不存在的端口
                description="不健康的测试服务器",
                health_check_url="http://localhost:9999/health",
                auto_connect=True
            )
        ]
        
        for server in test_servers:
            client.register_server_manually(server)
        
        # 启动动态功能（包括健康检查）
        await client.start_dynamic_features()
        
        print("\n💓 健康监控已启动...")
        print("监控服务器健康状态，每分钟检查一次")
        
        # 尝试连接服务器
        await client.connect_registered_servers()
        
        # 监控5分钟
        for i in range(10):  # 每30秒显示一次状态
            await asyncio.sleep(30)
            
            print(f"\n--- 健康检查 #{i+1} ---")
            client.show_registry_status()
            
            # 显示连接状态
            print("\n连接状态:")
            for name, server in client.servers.items():
                status = "已连接" if server.is_connected else "未连接"
                print(f"  {name}: {status}")
        
    except KeyboardInterrupt:
        print("\n👋 停止健康监控")
    except Exception as e:
        print(f"❌ 健康监控错误: {str(e)}")
    finally:
        await client.cleanup()


def create_sample_config():
    """创建示例配置文件"""
    config = {
        "client": {
            "registry_file": "mcp_registry.json",
            "api_key": "your-api-key-here",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        },
        "discovery": [
            {
                "type": "file_watch",
                "file_path": "discovered_servers.json",
                "interval": 10
            },
            {
                "type": "http_polling",
                "url": "http://localhost:9000/api/servers",
                "interval": 60
            }
        ],
        "servers": [
            {
                "name": "weather_service",
                "url": "http://localhost:8001",
                "description": "天气查询服务",
                "tags": ["weather", "api"],
                "priority": 10,
                "auto_connect": True
            },
            {
                "name": "file_service",
                "url": "http://localhost:8002",
                "description": "文件操作服务",
                "tags": ["file", "storage"],
                "priority": 8,
                "auto_connect": True
            }
        ]
    }
    
    with open("mcp_dynamic_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("✅ 示例配置文件已创建: mcp_dynamic_config.json")


async def main():
    """主函数"""
    print("🚀 MCP动态注册客户端演示程序")
    print("=" * 50)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建示例配置
    create_sample_config()
    
    while True:
        print("\n请选择演示模式:")
        print("1. 基本使用演示")
        print("2. 交互模式演示")
        print("3. 服务发现演示")
        print("4. 健康监控演示")
        print("5. 退出")
        
        try:
            choice = input("\n请输入选择 (1-5): ").strip()
            
            if choice == "1":
                await demo_basic_usage()
            elif choice == "2":
                await demo_interactive_mode()
            elif choice == "3":
                await demo_service_discovery()
            elif choice == "4":
                await demo_health_monitoring()
            elif choice == "5":
                print("👋 再见！")
                break
            else:
                print("❌ 无效选择，请重试")
        
        except KeyboardInterrupt:
            print("\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 程序错误: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())