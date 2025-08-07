from fastapi import WebSocket, WebSocketDisconnect
import json
import uuid
from typing import Dict
from services.ppt_service import PPTGenerationService
from services.document_service import DocumentProcessor

class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.ppt_service = PPTGenerationService()
        self.doc_processor = DocumentProcessor()
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        
        # 发送连接成功消息
        await websocket.send_text(json.dumps({
            "type": "connected",
            "client_id": client_id,
            "message": "连接成功"
        }, ensure_ascii=False))
    
    def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
    
    async def send_personal_message(self, message: str, client_id: str):
        """发送个人消息"""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)
    
    async def broadcast(self, message: str):
        """广播消息"""
        for connection in self.active_connections.values():
            await connection.send_text(message)
    
    async def handle_ppt_generation(self, websocket: WebSocket, data: dict):
        """处理PPT生成请求"""
        task_id = str(uuid.uuid4())
        
        try:
            async for progress_data in self.ppt_service.generate_ppt_stream(
                task_id=task_id,
                query=data["query"],
                reference_content=data.get("reference_content", ""),
                enable_rethink=data.get("enable_rethink", True),
                max_rethink_times=data.get("max_rethink_times", 3)
            ):
                await websocket.send_text(json.dumps(progress_data, ensure_ascii=False))
                
        except Exception as e:
            error_message = {
                "task_id": task_id,
                "status": "error",
                "progress": 0,
                "current_step": "error",
                "error_message": str(e)
            }
            await websocket.send_text(json.dumps(error_message, ensure_ascii=False))
    
    async def handle_file_upload(self, websocket: WebSocket, data: dict):
        """处理文件上传（通过WebSocket）"""
        try:
            # 这里可以实现通过WebSocket的文件上传逻辑
            # 由于WebSocket不直接支持文件上传，建议使用HTTP接口
            await websocket.send_text(json.dumps({
                "type": "file_upload_response",
                "message": "请使用HTTP接口上传文件",
                "success": False
            }, ensure_ascii=False))
            
        except Exception as e:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": str(e)
            }, ensure_ascii=False))