#!/usr/bin/env python3
"""
服务发现HTTP服务器示例

这个服务器提供HTTP API来管理MCP服务器的注册和发现。
其他MCP服务器可以通过这个API注册自己，客户端可以通过这个API发现可用的服务器。
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from aiohttp import web, ClientSession
import aiohttp_cors
import logging
from pathlib import Path


@dataclass
class ServerInfo:
    """服务器信息"""
    name: str
    url: str
    description: str = ""
    tags: List[str] = None
    priority: int = 0
    health_check_url: Optional[str] = None
    metadata: Dict[str, Any] = None
    registered_at: float = None
    last_heartbeat: float = None
    status: str = "unknown"  # unknown, healthy, unhealthy
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}
        if self.registered_at is None:
            self.registered_at = time.time()
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()


class DiscoveryServer:
    """服务发现服务器"""
    
    def __init__(self, data_file: str = "discovery_data.json"):
        self.servers: Dict[str, ServerInfo] = {}
        self.data_file = data_file
        self.health_check_task: Optional[asyncio.Task] = None
        self.load_data()
    
    def load_data(self):
        """加载数据"""
        try:
            if Path(self.data_file).exists():
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for server_data in data.get('servers', []):
                    server_info = ServerInfo(**server_data)
                    self.servers[server_info.name] = server_info
                
                logging.info(f"加载了 {len(self.servers)} 个服务器信息")
        except Exception as e:
            logging.error(f"加载数据失败: {str(e)}")
    
    def save_data(self):
        """保存数据"""
        try:
            data = {
                'servers': [asdict(server) for server in self.servers.values()],
                'last_updated': time.time()
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.error(f"保存数据失败: {str(e)}")
    
    async def register_server(self, server_data: Dict[str, Any]) -> Dict[str, Any]:
        """注册服务器"""
        try:
            server_info = ServerInfo(
                name=server_data['name'],
                url=server_data['url'],
                description=server_data.get('description', ''),
                tags=server_data.get('tags', []),
                priority=server_data.get('priority', 0),
                health_check_url=server_data.get('health_check_url'),
                metadata=server_data.get('metadata', {})
            )
            
            # 检查是否已存在
            if server_info.name in self.servers:
                # 更新现有服务器
                old_server = self.servers[server_info.name]
                server_info.registered_at = old_server.registered_at
                action = "updated"
            else:
                action = "registered"
            
            self.servers[server_info.name] = server_info
            self.save_data()
            
            logging.info(f"服务器 {server_info.name} {action}")
            
            return {
                'success': True,
                'action': action,
                'server': asdict(server_info)
            }
        
        except Exception as e:
            logging.error(f"注册服务器失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def unregister_server(self, server_name: str) -> Dict[str, Any]:
        """注销服务器"""
        try:
            if server_name in self.servers:
                del self.servers[server_name]
                self.save_data()
                
                logging.info(f"服务器 {server_name} 已注销")
                return {
                    'success': True,
                    'message': f'服务器 {server_name} 已注销'
                }
            else:
                return {
                    'success': False,
                    'error': f'服务器 {server_name} 不存在'
                }
        
        except Exception as e:
            logging.error(f"注销服务器失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def heartbeat(self, server_name: str) -> Dict[str, Any]:
        """服务器心跳"""
        try:
            if server_name in self.servers:
                self.servers[server_name].last_heartbeat = time.time()
                self.servers[server_name].status = "healthy"
                
                return {
                    'success': True,
                    'message': f'服务器 {server_name} 心跳更新'
                }
            else:
                return {
                    'success': False,
                    'error': f'服务器 {server_name} 不存在'
                }
        
        except Exception as e:
            logging.error(f"心跳更新失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def discover_servers(self, tags: List[str] = None, status: str = None) -> Dict[str, Any]:
        """发现服务器"""
        try:
            servers = list(self.servers.values())
            
            # 按标签过滤
            if tags:
                servers = [s for s in servers if any(tag in s.tags for tag in tags)]
            
            # 按状态过滤
            if status:
                servers = [s for s in servers if s.status == status]
            
            # 按优先级排序
            servers.sort(key=lambda x: x.priority, reverse=True)
            
            return {
                'success': True,
                'servers': [asdict(server) for server in servers],
                'total': len(servers),
                'timestamp': time.time()
            }
        
        except Exception as e:
            logging.error(f"发现服务器失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """获取服务器信息"""
        try:
            if server_name in self.servers:
                return {
                    'success': True,
                    'server': asdict(self.servers[server_name])
                }
            else:
                return {
                    'success': False,
                    'error': f'服务器 {server_name} 不存在'
                }
        
        except Exception as e:
            logging.error(f"获取服务器信息失败: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def start_health_check(self):
        """启动健康检查"""
        self.health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def stop_health_check(self):
        """停止健康检查"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass
    
    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(30)  # 每30秒检查一次
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"健康检查错误: {str(e)}")
    
    async def _perform_health_checks(self):
        """执行健康检查"""
        current_time = time.time()
        
        for server_name, server_info in self.servers.items():
            # 检查心跳超时
            if current_time - server_info.last_heartbeat > 120:  # 2分钟超时
                server_info.status = "unhealthy"
                logging.warning(f"服务器 {server_name} 心跳超时")
                continue
            
            # 如果有健康检查URL，执行HTTP检查
            if server_info.health_check_url:
                try:
                    async with ClientSession() as session:
                        async with session.get(
                            server_info.health_check_url,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            if response.status == 200:
                                server_info.status = "healthy"
                            else:
                                server_info.status = "unhealthy"
                                logging.warning(f"服务器 {server_name} 健康检查失败: {response.status}")
                except Exception as e:
                    server_info.status = "unhealthy"
                    logging.warning(f"服务器 {server_name} 健康检查异常: {str(e)}")
        
        # 保存状态更新
        self.save_data()


# HTTP API 处理器
async def register_handler(request):
    """注册服务器API"""
    try:
        data = await request.json()
        result = await request.app['discovery'].register_server(data)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=400)


async def unregister_handler(request):
    """注销服务器API"""
    try:
        server_name = request.match_info['name']
        result = await request.app['discovery'].unregister_server(server_name)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=400)


async def heartbeat_handler(request):
    """心跳API"""
    try:
        server_name = request.match_info['name']
        result = await request.app['discovery'].heartbeat(server_name)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=400)


async def discover_handler(request):
    """发现服务器API"""
    try:
        # 获取查询参数
        tags = request.query.get('tags')
        if tags:
            tags = tags.split(',')
        
        status = request.query.get('status')
        
        result = await request.app['discovery'].discover_servers(tags=tags, status=status)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=400)


async def server_info_handler(request):
    """获取服务器信息API"""
    try:
        server_name = request.match_info['name']
        result = await request.app['discovery'].get_server_info(server_name)
        return web.json_response(result)
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=400)


async def status_handler(request):
    """服务状态API"""
    try:
        discovery = request.app['discovery']
        servers = list(discovery.servers.values())
        
        status_counts = {
            'healthy': len([s for s in servers if s.status == 'healthy']),
            'unhealthy': len([s for s in servers if s.status == 'unhealthy']),
            'unknown': len([s for s in servers if s.status == 'unknown'])
        }
        
        return web.json_response({
            'success': True,
            'total_servers': len(servers),
            'status_counts': status_counts,
            'uptime': time.time() - request.app['start_time'],
            'timestamp': time.time()
        })
    except Exception as e:
        return web.json_response({
            'success': False,
            'error': f'请求处理失败: {str(e)}'
        }, status=500)


async def init_app():
    """初始化应用"""
    app = web.Application()
    
    # 创建发现服务器实例
    discovery = DiscoveryServer()
    app['discovery'] = discovery
    app['start_time'] = time.time()
    
    # 设置路由
    app.router.add_post('/api/register', register_handler)
    app.router.add_delete('/api/servers/{name}', unregister_handler)
    app.router.add_post('/api/servers/{name}/heartbeat', heartbeat_handler)
    app.router.add_get('/api/discover', discover_handler)
    app.router.add_get('/api/servers/{name}', server_info_handler)
    app.router.add_get('/api/status', status_handler)
    
    # 设置CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
            allow_methods="*"
        )
    })
    
    # 为所有路由添加CORS
    for route in list(app.router.routes()):
        cors.add(route)
    
    # 启动健康检查
    await discovery.start_health_check()
    
    return app


async def cleanup_app(app):
    """清理应用"""
    await app['discovery'].stop_health_check()


def main():
    """主函数"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # 创建和运行应用
    app = init_app()
    
    try:
        print("🚀 服务发现服务器启动中...")
        print("📡 API端点:")
        print("  POST   /api/register              - 注册服务器")
        print("  DELETE /api/servers/{name}       - 注销服务器")
        print("  POST   /api/servers/{name}/heartbeat - 服务器心跳")
        print("  GET    /api/discover             - 发现服务器")
        print("  GET    /api/servers/{name}       - 获取服务器信息")
        print("  GET    /api/status               - 服务状态")
        print("\n🌐 服务器地址: http://localhost:8080")
        print("按 Ctrl+C 停止服务器")
        
        web.run_app(
            app,
            host='localhost',
            port=8080,
            cleanup_handler=cleanup_app
        )
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")


if __name__ == '__main__':
    main()