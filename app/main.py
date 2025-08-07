from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
import uuid
import os
from pathlib import Path

# 导入服务层
from services.document_service import DocumentProcessor
from services.ppt_service import PPTGenerationService
from api.websocket import ConnectionManager
from models.schemas import PPTRequest, PPTResponse, FileUploadResponse

app = FastAPI(
    title="PPT生成系统",
    description="基于AI的智能PPT生成系统",
    version="1.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化服务
document_processor = DocumentProcessor()
ppt_service = PPTGenerationService()
connection_manager = ConnectionManager()

# 确保临时文件夹存在
temp_dir = Path("temp")
temp_dir.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "PPT生成系统API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload-files", response_model=List[FileUploadResponse])
async def upload_files(files: List[UploadFile] = File(...)):
    """上传并处理文档文件"""
    try:
        results = []
        for file in files:
            result = await document_processor.process_file(file)
            results.append(FileUploadResponse(
                filename=result["filename"],
                file_type=result["file_type"],
                size=result["size"],
                content_preview=result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"],
                success=True
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/generate-ppt", response_model=PPTResponse)
async def generate_ppt_sync(request: PPTRequest):
    """同步PPT生成接口（用于简单场景）"""
    try:
        task_id = str(uuid.uuid4())
        # 这里可以实现同步版本的生成逻辑
        return PPTResponse(
            task_id=task_id,
            status="processing",
            progress=0,
            current_step="started"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket连接端点"""
    await connection_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "generate_ppt":
                await connection_manager.handle_ppt_generation(websocket, message["data"])
            elif message["type"] == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": str(e)
        }))
        connection_manager.disconnect(client_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)