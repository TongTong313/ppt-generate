#!/usr/bin/env python3
"""API测试脚本"""

import asyncio
import aiohttp
import json
from pathlib import Path

async def test_health():
    """测试健康检查接口"""
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8000/health") as response:
            result = await response.json()
            print(f"Health check: {result}")

async def test_file_upload():
    """测试文件上传接口"""
    # 创建测试文件
    test_file = Path("test.txt")
    test_file.write_text("这是一个测试文件内容")
    
    try:
        async with aiohttp.ClientSession() as session:
            with open(test_file, 'rb') as f:
                data = aiohttp.FormData()
                data.add_field('files', f, filename='test.txt')
                
                async with session.post("http://localhost:8000/upload-files", data=data) as response:
                    result = await response.json()
                    print(f"File upload: {result}")
    finally:
        test_file.unlink(missing_ok=True)

async def test_websocket():
    """测试WebSocket连接"""
    import websockets
    
    uri = "ws://localhost:8000/ws/test-client"
    
    try:
        async with websockets.connect(uri) as websocket:
            # 发送PPT生成请求
            request = {
                "type": "generate_ppt",
                "data": {
                    "query": "生成一个关于Python编程的PPT，不超过5页",
                    "reference_content": "Python是一种高级编程语言",
                    "enable_rethink": True,
                    "max_rethink_times": 2
                }
            }
            
            await websocket.send(json.dumps(request))
            
            # 接收响应
            while True:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=60)
                    data = json.loads(response)
                    print(f"Received: {data}")
                    
                    if data.get("status") in ["completed", "error"]:
                        break
                        
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                    
    except Exception as e:
        print(f"WebSocket test failed: {e}")

async def main():
    """运行所有测试"""
    print("开始API测试...")
    
    await test_health()
    await test_file_upload()
    await test_websocket()
    
    print("测试完成")

if __name__ == "__main__":
    asyncio.run(main())