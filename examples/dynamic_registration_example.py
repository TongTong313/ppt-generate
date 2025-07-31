#!/usr/bin/env python3
"""
动态MCP服务器注册完整示例

这个示例展示了如何使用动态注册功能：
1. 手动注册服务器
2. 通过文件监控自动发现服务器
3. 通过HTTP API发现服务器
4. 健康检查和自动重连
5. 服务器优先级和标签管理
"""

import asyncio
import sys
import os
import json
import logging
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ppt_generate.dynamic_mcp_client import DynamicMCPClient, ServerRegistration


async def manual_registration_example():
    """手动注册示例"""
    print("=== 手动注册服务器示例 ===")
    
    client = DynamicMCPClient(
        registry_file="examples/manual_registry.json"
    )
    
    try:
        # 手动注册多个服务器
        servers_to_register = [
            ServerRegistration(
                name="weather_service",
                url="http://localhost:8001",
                description="天气查询服务",
                tags=["weather", "api", "external"],
                priority=10,
                auto_connect=True,
                health_check_url="http://localhost:8001/health",
                metadata={
                    "version": "1.0.0",
                    "provider": "WeatherAPI",
                    "rate_limit": "1000/hour"
                }
            ),
            ServerRegistration(
                name="database_service",
                url="http://localhost:8002",
                description="数据库操作服务",
                tags=["database", "storage", "internal"],
                priority=8,
                auto_connect=True,
                health_check_url="http://localhost:8002/health",
                metadata={
                    "version": "2.1.0",
                    "database_type": "postgresql",
                    "max_connections": 100
                }
            ),
            ServerRegistration(
                name="ai_service",
                url="http://localhost:8003",
                description="AI推理服务",
                tags=["ai", "ml", "gpu"],
                priority=15,  # 高优先级
                auto_connect=False,  # 手动连接
                health_check_url="http://localhost:8003/health",
                metadata={
                    "version": "3.0.0",
                    "model_type": "transformer",
                    "gpu_required": True
                }
            )
        ]
        
        # 注册所有服务器
        for server in servers_to_register:
            success = client.register_server_manually(server)
            if success:
                print(f"✅ 成功注册: {server.name}")
            else:
                print(f"❌ 注册失败: {server.name}")
        
        # 显示注册状态
        client.show_registry_status()
        
        # 连接自动连接的服务器
        print("\n🔄 连接设置为自动连接的服务器...")
        await client.connect_registered_servers(auto_connect_only=True)
        
        # 手动连接AI服务
        print("\n🔧 手动连接AI服务...")
        await client.connect_server("ai_service")
        
        # 显示最终状态
        client.show_status()
        
        # 演示按标签查询
        print("\n🏷️ 按标签查询服务器:")
        ai_servers = client.get_registered_servers(tags=["ai"])
        print(f"AI服务器: {[s.name for s in ai_servers]}")
        
        api_servers = client.get_registered_servers(tags=["api"])
        print(f"API服务器: {[s.name for s in api_servers]}")
        
    except Exception as e:
        print(f"❌ 手动注册示例失败: {str(e)}")
    finally:
        await client.cleanup()


async def file_discovery_example():
    """文件发现示例"""
    print("\n=== 文件监控服务发现示例 ===")
    
    client = DynamicMCPClient(
        registry_file="examples/file_discovery_registry.json"
    )
    
    try:
        # 配置文件监控发现
        discovery_configs = [
            {
                'type': 'file_watch',
                'name': 'local_file_discovery',
                'file_path': 'examples/discovered_servers.json',
                'interval': 5  # 每5秒检查一次文件变化
            }
        ]
        
        # 启动动态功能
        await client.start_dynamic_features(discovery_configs)
        
        print("📁 文件监控已启动，监控文件: examples/discovered_servers.json")
        print("💡 提示: 修改该文件来模拟服务发现")
        
        # 等待一段时间让文件发现工作
        print("⏳ 等待10秒让服务发现工作...")
        await asyncio.sleep(10)
        
        # 显示发现的服务器
        client.show_registry_status()
        
        # 连接发现的服务器
        print("\n🔄 连接通过文件发现的服务器...")
        await client.connect_registered_servers()
        
        client.show_status()
        
        # 演示动态更新
        print("\n📝 演示动态更新...")
        print("现在你可以修改 examples/discovered_servers.json 文件")
        print("客户端会自动检测变化并更新服务器列表")
        
        # 继续监控一段时间
        print("⏳ 继续监控30秒...")
        await asyncio.sleep(30)
        
        # 显示最终状态
        print("\n📊 最终状态:")
        client.show_registry_status()
        
    except Exception as e:
        print(f"❌ 文件发现示例失败: {str(e)}")
    finally:
        await client.cleanup()


async def http_discovery_example():
    """HTTP发现示例"""
    print("\n=== HTTP API服务发现示例 ===")
    
    client = DynamicMCPClient(
        registry_file="examples/http_discovery_registry.json"
    )
    
    try:
        # 配置HTTP轮询发现
        discovery_configs = [
            {
                'type': 'http_polling',
                'name': 'discovery_server',
                'url': 'http://localhost:8080/api/discover',
                'interval': 15  # 每15秒轮询一次
            }
        ]
        
        print("🌐 HTTP发现配置:")
        print("   发现服务器: http://localhost:8080")
        print("   轮询间隔: 15秒")
        print("\n💡 提示: 请确保发现服务器正在运行")
        print("   运行命令: python examples/discovery_server.py")
        
        # 启动动态功能
        await client.start_dynamic_features(discovery_configs)
        
        # 等待HTTP发现工作
        print("\n⏳ 等待HTTP发现工作...")
        await asyncio.sleep(20)
        
        # 显示发现的服务器
        client.show_registry_status()
        
        # 连接发现的服务器
        print("\n🔄 连接通过HTTP发现的服务器...")
        await client.connect_registered_servers()
        
        client.show_status()
        
    except Exception as e:
        print(f"❌ HTTP发现示例失败: {str(e)}")
        print("💡 请确保发现服务器正在运行: python examples/discovery_server.py")
    finally:
        await client.cleanup()


async def comprehensive_example():
    """综合示例 - 使用所有功能"""
    print("\n=== 综合动态注册示例 ===")
    
    client = DynamicMCPClient(
        config_file="examples/servers_config.json",
        registry_file="examples/comprehensive_registry.json"
    )
    
    try:
        # 1. 手动注册一些核心服务器
        print("📝 1. 手动注册核心服务器...")
        core_servers = [
            ServerRegistration(
                name="core_auth",
                url="http://localhost:7001",
                description="核心认证服务",
                tags=["auth", "security", "core"],
                priority=20,  # 最高优先级
                auto_connect=True
            ),
            ServerRegistration(
                name="core_logging",
                url="http://localhost:7002",
                description="核心日志服务",
                tags=["logging", "monitoring", "core"],
                priority=18,
                auto_connect=True
            )
        ]
        
        for server in core_servers:
            client.register_server_manually(server)
        
        # 2. 配置多种服务发现
        print("🔍 2. 配置服务发现...")
        discovery_configs = [
            {
                'type': 'file_watch',
                'name': 'file_discovery',
                'file_path': 'examples/discovered_servers.json',
                'interval': 5
            },
            {
                'type': 'http_polling',
                'name': 'http_discovery',
                'url': 'http://localhost:8080/api/discover',
                'interval': 20
            }
        ]
        
        # 3. 启动所有动态功能
        print("🚀 3. 启动动态功能...")
        await client.start_dynamic_features(discovery_configs)
        
        # 4. 连接已注册的服务器
        print("🔄 4. 连接已注册的服务器...")
        await client.connect_registered_servers()
        
        # 5. 显示初始状态
        print("\n📊 5. 初始状态:")
        client.show_registry_status()
        client.show_status()
        
        # 6. 模拟运行和监控
        print("\n⏰ 6. 运行监控 (60秒)...")
        print("   - 健康检查每60秒执行一次")
        print("   - 文件发现每5秒检查一次")
        print("   - HTTP发现每20秒轮询一次")
        print("   - 清理任务每5分钟执行一次")
        
        # 分阶段显示状态
        for i in range(6):
            await asyncio.sleep(10)
            print(f"\n⏱️ 运行时间: {(i+1)*10}秒")
            
            # 每20秒显示一次详细状态
            if (i + 1) % 2 == 0:
                print("📊 当前状态:")
                client.show_registry_status()
                
                # 显示按标签分组的服务器
                all_servers = client.get_registered_servers()
                tags_summary = {}
                for server in all_servers:
                    for tag in server.tags:
                        if tag not in tags_summary:
                            tags_summary[tag] = []
                        tags_summary[tag].append(server.name)
                
                print("\n🏷️ 按标签分组:")
                for tag, servers in tags_summary.items():
                    print(f"  {tag}: {', '.join(servers)}")
        
        # 7. 演示动态操作
        print("\n🔧 7. 演示动态操作...")
        
        # 手动注册一个临时服务器
        temp_server = ServerRegistration(
            name="temp_service",
            url="http://localhost:9999",
            description="临时测试服务",
            tags=["temp", "test"],
            priority=1,
            auto_connect=False
        )
        
        client.register_server_manually(temp_server)
        print("✅ 注册临时服务器")
        
        await asyncio.sleep(5)
        
        # 注销临时服务器
        client.unregister_server_manually("temp_service")
        print("🗑️ 注销临时服务器")
        
        # 8. 最终状态
        print("\n📊 8. 最终状态:")
        client.show_registry_status()
        client.show_status()
        
        # 9. 性能统计
        print("\n📈 9. 性能统计:")
        all_servers = client.get_registered_servers()
        connected_servers = client.get_connected_servers()
        
        print(f"   总注册服务器: {len(all_servers)}")
        print(f"   已连接服务器: {len(connected_servers)}")
        print(f"   连接成功率: {len(connected_servers)/len(all_servers)*100:.1f}%" if all_servers else "N/A")
        
        # 按优先级统计
        priority_stats = {}
        for server in all_servers:
            priority = server.priority
            if priority not in priority_stats:
                priority_stats[priority] = 0
            priority_stats[priority] += 1
        
        print("\n🎯 优先级分布:")
        for priority in sorted(priority_stats.keys(), reverse=True):
            count = priority_stats[priority]
            print(f"   优先级 {priority}: {count} 个服务器")
        
    except Exception as e:
        print(f"❌ 综合示例失败: {str(e)}")
    finally:
        await client.cleanup()


async def interactive_example():
    """交互式示例"""
    print("\n=== 交互式动态注册示例 ===")
    print("这将启动一个交互式会话，你可以体验所有动态功能")
    
    response = input("\n是否继续? (y/N): ").strip().lower()
    if response != 'y':
        print("已取消交互式示例")
        return
    
    client = DynamicMCPClient(
        config_file="examples/servers_config.json",
        registry_file="examples/interactive_registry.json"
    )
    
    try:
        # 预注册一些服务器
        print("📝 预注册示例服务器...")
        example_servers = [
            ServerRegistration(
                name="example_weather",
                url="http://localhost:8001",
                description="示例天气服务",
                tags=["weather", "example"],
                priority=5,
                auto_connect=True
            ),
            ServerRegistration(
                name="example_calculator",
                url="http://localhost:8002",
                description="示例计算服务",
                tags=["math", "example"],
                priority=3,
                auto_connect=True
            )
        ]
        
        for server in example_servers:
            client.register_server_manually(server)
        
        # 配置服务发现
        discovery_configs = [
            {
                'type': 'file_watch',
                'name': 'interactive_discovery',
                'file_path': 'examples/discovered_servers.json',
                'interval': 3
            }
        ]
        
        # 启动动态功能
        await client.start_dynamic_features(discovery_configs)
        
        # 连接服务器
        await client.connect_registered_servers()
        
        print("\n🎮 交互式命令:")
        print("  'registry' - 显示注册状态")
        print("  'status'   - 显示连接状态")
        print("  'config'   - 显示配置")
        print("  'tools'    - 显示可用工具")
        print("  'quit'     - 退出")
        print("  其他输入   - 发送给AI处理")
        
        # 启动交互式聊天（增强版）
        await client.chat_loop()
        
    except KeyboardInterrupt:
        print("\n👋 用户中断，正在退出...")
    except Exception as e:
        print(f"❌ 交互式示例失败: {str(e)}")
    finally:
        await client.cleanup()


async def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 动态MCP服务器注册示例程序")
    print("=" * 60)
    
    examples = [
        ("1", "手动注册示例", manual_registration_example),
        ("2", "文件发现示例", file_discovery_example),
        ("3", "HTTP发现示例", http_discovery_example),
        ("4", "综合功能示例", comprehensive_example),
        ("5", "交互式示例", interactive_example),
        ("a", "运行所有示例", None)
    ]
    
    print("\n📋 可用示例:")
    for key, name, _ in examples:
        print(f"  {key}. {name}")
    
    choice = input("\n请选择要运行的示例 (1-5, a): ").strip().lower()
    
    if choice == 'a':
        # 运行所有示例
        for key, name, func in examples[:-2]:  # 排除交互式和"运行所有"
            print(f"\n{'='*60}")
            print(f"运行示例: {name}")
            print(f"{'='*60}")
            try:
                await func()
            except Exception as e:
                print(f"❌ 示例 {name} 失败: {str(e)}")
            
            if key != "4":  # 不是最后一个
                input("\n按回车键继续下一个示例...")
    else:
        # 运行单个示例
        for key, name, func in examples:
            if choice == key and func:
                print(f"\n{'='*60}")
                print(f"运行示例: {name}")
                print(f"{'='*60}")
                try:
                    await func()
                except Exception as e:
                    print(f"❌ 示例失败: {str(e)}")
                break
        else:
            print("❌ 无效选择")
    
    print("\n✅ 示例程序完成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序执行失败: {str(e)}")