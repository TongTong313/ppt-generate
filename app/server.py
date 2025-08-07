#!/usr/bin/env python3
"""
PPT生成器后端服务
提供RESTful API接口供前端调用
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional

from aiohttp import web, web_ws
from aiohttp_cors import setup as cors_setup, ResourceOptions

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ppt_generate.agents.ppt_agent import PPTAgent


class PPTServer:
    """PPT生成服务器"""
    
    def __init__(self):
        self.app = web.Application()
        self.ppt_agent = None
        self.setup_routes()
        self.setup_cors()
    
    def setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_post('/api/generate-outline', self.generate_outline)
        self.app.router.add_post('/api/generate-content', self.generate_content)
        self.app.router.add_get('/api/ws', self.websocket_handler)
        
        # 静态文件服务
        self.app.router.add_static('/', path=Path(__file__).parent, name='static')
    
    def setup_cors(self):
        """设置CORS"""
        cors = cors_setup(self.app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # 为所有路由添加CORS
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    async def index(self, request):
        """首页"""
        index_path = Path(__file__).parent / 'index.html'
        return web.FileResponse(index_path)
    
    async def generate_outline(self, request):
        """生成PPT大纲"""
        try:
            data = await request.json()
            query = data.get('query', '')
            reference_content = data.get('reference_content', '')
            
            if not query:
                return web.json_response(
                    {'error': '请提供PPT主题需求'}, 
                    status=400
                )
            
            # 初始化PPT代理
            if not self.ppt_agent:
                self.ppt_agent = PPTAgent()
            
            # 生成大纲
            await self.ppt_agent.generate_ppt_outline(
                query=query,
                reference_content=reference_content if reference_content else None
            )
            
            outline = self.ppt_agent.ppt_info.get('outline', '')
            
            return web.json_response({
                'success': True,
                'outline': outline,
                'message': '大纲生成成功'
            })
            
        except Exception as e:
            return web.json_response(
                {'error': f'生成大纲失败: {str(e)}'}, 
                status=500
            )
    
    async def generate_content(self, request):
        """生成PPT内容"""
        try:
            data = await request.json()
            outline = data.get('outline', '')
            reference_content = data.get('reference_content', '')
            
            if not outline:
                return web.json_response(
                    {'error': '请先生成PPT大纲'}, 
                    status=400
                )
            
            # 确保PPT代理已初始化
            if not self.ppt_agent:
                self.ppt_agent = PPTAgent()
                self.ppt_agent.ppt_info['outline'] = outline
            
            # 生成页面内容
            await self.ppt_agent.generate_page_content(
                outline=outline,
                reference_content=reference_content if reference_content else None
            )
            
            pages = self.ppt_agent.ppt_info.get('pages', [])
            
            return web.json_response({
                'success': True,
                'pages': pages,
                'message': 'PPT内容生成成功'
            })
            
        except Exception as e:
            return web.json_response(
                {'error': f'生成内容失败: {str(e)}'}, 
                status=500
            )
    
    async def websocket_handler(self, request):
        """WebSocket处理器，用于实时流式输出"""
        ws = web_ws.WebSocketResponse()
        await ws.prepare(request)
        
        try:
            async for msg in ws:
                if msg.type == web_ws.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    action = data.get('action')
                    
                    if action == 'generate_outline':
                        await self.stream_outline_generation(ws, data)
                    elif action == 'generate_content':
                        await self.stream_content_generation(ws, data)
                    
                elif msg.type == web_ws.WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
                    break
                elif msg.type == web_ws.WSMsgType.CLOSE:
                    print('WebSocket连接已关闭')
                    break
                    
        except Exception as e:
            print(f'WebSocket处理错误: {e}')
        finally:
            if not ws.closed:
                await ws.close()
        
        return ws
    
    async def safe_send_ws_message(self, ws, message):
        """安全发送WebSocket消息，检查连接状态"""
        try:
            if not ws.closed:
                await ws.send_str(json.dumps(message))
            else:
                print('WebSocket已关闭，跳过消息发送')
        except Exception as e:
            print(f'发送WebSocket消息失败: {e}')
    
    async def stream_outline_generation(self, ws, data):
        """流式生成大纲"""
        try:
            query = data.get('query', '')
            reference_content = data.get('reference_content', '')
            
            # 初始化PPT代理
            if not self.ppt_agent:
                self.ppt_agent = PPTAgent()
            
            # 检查API密钥
            if not self.ppt_agent.api_key:
                # 如果没有API密钥，使用模拟数据
                await self._simulate_outline_generation(ws, query)
                return
            
            # 真实调用PPTAgent生成大纲
            await self._real_outline_generation(ws, query, reference_content)
            
        except Exception as e:
            await self.safe_send_ws_message(ws, {
                'type': 'error',
                'message': f'生成大纲失败: {str(e)}'
            })
    
    async def _real_outline_generation(self, ws, query, reference_content):
        """真实的大纲生成"""
        from openai import AsyncOpenAI
        from ppt_generate.prompts.system_prompt import PPT_OUTLINE_PROMPT
        import re
        
        messages = [
            {"role": "system", "content": PPT_OUTLINE_PROMPT},
            {
                "role": "user",
                "content": f"用户需求：{query}\n参考内容：{reference_content if reference_content else '无'}",
            },
        ]

        # 流式输出
        response = await self.ppt_agent.llm.chat.completions.create(
            model=self.ppt_agent.model,
            max_tokens=self.ppt_agent.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.ppt_agent.temperature,
            stream=True,
            extra_body={"enable_thinking": True},
        )

        # 收集思考内容和回复内容
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        # 发送思考开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'thinking_start',
            'message': '开始分析需求...'
        })

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            
            # 处理思考内容
            if (
                hasattr(delta, "reasoning_content")
                and delta.reasoning_content is not None
            ):
                if not is_answering:
                    await self.safe_send_ws_message(ws, {
                        'type': 'thinking',
                        'content': delta.reasoning_content
                    })
                reasoning_content += delta.reasoning_content

            # 处理回复内容
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    await self.safe_send_ws_message(ws, {
                        'type': 'generating_start',
                        'message': '开始生成大纲...'
                    })
                    is_answering = True
                
                # 发送大纲生成过程
                await self.safe_send_ws_message(ws, {
                    'type': 'outline_generating',
                    'content': delta.content
                })
                answer_content += delta.content

        # 从完整内容中提取大纲部分
        outline_match = re.search(
            r"<outline>(.*?)</outline>", answer_content, re.DOTALL
        )
        if outline_match:
            outline = outline_match.group(1).strip()
            self.ppt_agent.ppt_info["outline"] = outline
            
            # 发送完成信号
            await self.safe_send_ws_message(ws, {
                'type': 'outline_complete',
                'outline': f"<outline>{outline}</outline>"
            })
        else:
            raise ValueError("未能在输出中找到大纲内容")
    
    async def _simulate_outline_generation(self, ws, query):
        """模拟大纲生成（无API密钥时使用）"""
        # 发送开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'thinking_start',
            'message': '开始分析需求...'
        })
        
        # 模拟思考过程
        thinking_steps = [
            '正在分析用户需求...',
            '解析参考内容...',
            '确定PPT主题和结构...',
            '生成大纲框架...',
            '优化大纲逻辑...',
        ]
        
        for step in thinking_steps:
            await self.safe_send_ws_message(ws, {
                'type': 'thinking',
                'content': step
            })
            await asyncio.sleep(0.8)
        
        # 发送生成开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'generating_start',
            'message': '开始生成大纲...'
        })
        
        sample_outline = f"""
<outline>
1. {query}的背景介绍
   - 历史发展概述
   - 当前发展现状
   - 重要性和意义

2. 核心概念和原理
   - 基本定义和概念
   - 核心技术原理
   - 关键特征分析

3. 应用场景和案例
   - 主要应用领域
   - 典型应用案例
   - 成功实践经验

4. 发展趋势和展望
   - 技术发展趋势
   - 市场前景分析
   - 未来发展方向

5. 总结和思考
   - 关键要点总结
   - 启示和思考
   - 行动建议
</outline>
        """
        
        # 保存大纲
        if not self.ppt_agent:
            self.ppt_agent = PPTAgent()
        self.ppt_agent.ppt_info['outline'] = sample_outline
        
        # 发送完成信号
        await self.safe_send_ws_message(ws, {
            'type': 'outline_complete',
            'outline': sample_outline
        })
    
    async def stream_content_generation(self, ws, data):
        """流式生成内容"""
        try:
            outline = data.get('outline', '')
            reference_content = data.get('reference_content', '')
            
            # 初始化PPT代理
            if not self.ppt_agent:
                self.ppt_agent = PPTAgent()
            
            # 检查API密钥
            if not self.ppt_agent.api_key:
                # 如果没有API密钥，使用模拟数据
                await self._simulate_content_generation(ws, outline)
                return
            
            # 真实调用PPTAgent生成内容
            await self._real_content_generation(ws, outline, reference_content)
            
        except Exception as e:
            await self.safe_send_ws_message(ws, {
                'type': 'error',
                'message': f'生成内容失败: {str(e)}'
            })
    
    async def _real_content_generation(self, ws, outline, reference_content):
        """真实的内容生成"""
        from ppt_generate.prompts.system_prompt import PPT_PAGE_CONTENT_PROMPT
        import re
        
        messages = [
            {"role": "system", "content": PPT_PAGE_CONTENT_PROMPT},
            {
                "role": "user",
                "content": f"大纲内容：{outline}\n参考内容：{reference_content if reference_content else '无'}",
            },
        ]

        # 流式输出
        response = await self.ppt_agent.llm.chat.completions.create(
            model=self.ppt_agent.model,
            max_tokens=self.ppt_agent.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.ppt_agent.temperature,
            stream=True,
            extra_body={"enable_thinking": True},
        )

        # 收集思考内容和回复内容
        reasoning_content = ""
        answer_content = ""
        is_answering = False
        
        # 发送思考开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'thinking_start',
            'message': '开始分析大纲...'
        })

        async for chunk in response:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta
            
            # 处理思考内容
            if (
                hasattr(delta, "reasoning_content")
                and delta.reasoning_content is not None
            ):
                if not is_answering:
                    await self.safe_send_ws_message(ws, {
                        'type': 'thinking',
                        'content': delta.reasoning_content
                    })
                reasoning_content += delta.reasoning_content

            # 处理回复内容
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    await self.safe_send_ws_message(ws, {
                        'type': 'generating_start',
                        'message': '开始生成页面内容...'
                    })
                    is_answering = True
                
                # 发送内容生成过程
                await self.safe_send_ws_message(ws, {
                    'type': 'content_generating',
                    'content': delta.content
                })
                answer_content += delta.content

        # 解析页面内容
        page_content_match = re.findall(
            r"<page>(.*?)</page>", answer_content, re.DOTALL
        )
        
        if page_content_match:
            pages = []
            for i, page_content in enumerate(page_content_match):
                # 解析每页的结构化内容
                page_data = self._parse_page_content(page_content.strip())
                pages.append(page_data)
                
                # 发送每页生成完成的信号
                await self.safe_send_ws_message(ws, {
                    'type': 'page_generated',
                    'page': page_data,
                    'page_number': i + 1
                })
                await asyncio.sleep(0.5)  # 短暂延迟以模拟逐页生成
            
            # 保存页面内容
            self.ppt_agent.ppt_info['pages'] = pages
            
            # 发送完成信号
            await self.safe_send_ws_message(ws, {
                'type': 'content_complete',
                'pages': pages
            })
        else:
            raise ValueError("未能在输出中找到页面内容")
    
    def _parse_page_content(self, page_content):
        """解析页面内容结构"""
        import re
        
        # 提取标题
        title_match = re.search(r'<title>(.*?)</title>', page_content, re.DOTALL)
        title = title_match.group(1).strip() if title_match else '未知标题'
        
        # 提取摘要
        summary_match = re.search(r'<summary>(.*?)</summary>', page_content, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ''
        
        # 提取正文
        body_match = re.search(r'<body>(.*?)</body>', page_content, re.DOTALL)
        body = body_match.group(1).strip() if body_match else ''
        
        # 提取建议
        advice_match = re.search(r'<advice>(.*?)</advice>', page_content, re.DOTALL)
        advice = advice_match.group(1).strip() if advice_match else ''
        
        return {
            'title': title,
            'summary': summary,
            'body': body,
            'advice': advice
        }
    
    async def _simulate_content_generation(self, ws, outline):
        """模拟内容生成（无API密钥时使用）"""
        # 发送开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'thinking_start',
            'message': '开始分析大纲...'
        })
        
        # 模拟思考过程
        thinking_steps = [
            '分析PPT大纲结构...',
            '规划页面布局和内容...',
            '生成开头页内容...',
            '生成目录页内容...',
            '生成正文页面内容...',
            '生成结尾页内容...',
            '优化页面内容和格式...'
        ]
        
        for step in thinking_steps:
            await self.safe_send_ws_message(ws, {
                'type': 'thinking',
                'content': step
            })
            await asyncio.sleep(1.0)
        
        # 发送生成开始信号
        await self.safe_send_ws_message(ws, {
            'type': 'generating_start',
            'message': '开始生成页面内容...'
        })
        
        # 模拟生成页面内容
        sample_pages = [
            {
                'title': '人工智能发展历程',
                'summary': '本次汇报将全面介绍人工智能的发展历程、核心技术和未来展望',
                'body': '汇报单位：XX科技公司\n汇报时间：2024年1月\n汇报人：张三',
                'advice': '开头页通常不需要添加图片或表格'
            },
            {
                'title': '目录',
                'summary': '本PPT的主要内容结构和章节安排',
                'body': '1. 人工智能背景介绍\n2. 核心概念和原理\n3. 应用场景和案例\n4. 发展趋势和展望\n5. 总结和思考',
                'advice': '目录页通常不需要添加图片或表格'
            },
            {
                'title': '人工智能背景介绍',
                'summary': '介绍人工智能的历史发展、现状和重要意义',
                'body': '1. 历史发展概述：人工智能概念最早由图灵在1950年提出，经历了多次发展浪潮...\n\n2. 当前发展现状：目前人工智能已经在图像识别、自然语言处理等领域取得显著成果...\n\n3. 重要性和意义：人工智能被认为是第四次工业革命的核心驱动力...',
                'advice': '建议添加人工智能发展时间线图表，展示重要里程碑事件'
            }
        ]
        
        # 逐页发送内容
        for i, page in enumerate(sample_pages):
            await self.safe_send_ws_message(ws, {
                'type': 'page_generated',
                'page': page,
                'page_number': i + 1
            })
            await asyncio.sleep(1.5)
        
        # 保存页面内容
        if not self.ppt_agent:
            self.ppt_agent = PPTAgent()
        self.ppt_agent.ppt_info['pages'] = sample_pages
        
        # 发送完成信号
        await self.safe_send_ws_message(ws, {
            'type': 'content_complete',
            'pages': sample_pages
        })
    
    def run(self, host='localhost', port=8080):
        """运行服务器"""
        print(f"PPT生成器服务启动: http://{host}:{port}")
        print("按 Ctrl+C 停止服务")
        
        web.run_app(
            self.app,
            host=host,
            port=port,
            access_log=None  # 禁用访问日志以减少输出
        )


def main():
    """主函数"""
    # 检查环境变量
    if not os.getenv('DASHSCOPE_API_KEY'):
        print("警告: 未设置 DASHSCOPE_API_KEY 环境变量")
        print("请设置API密钥: export DASHSCOPE_API_KEY='your-api-key'")
        print("当前将使用模拟数据进行演示")
    
    server = PPTServer()
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\n服务已停止")


if __name__ == '__main__':
    main()