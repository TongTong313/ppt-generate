from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum

class PPTRequest(BaseModel):
    """PPT生成请求模型"""
    query: str
    reference_content: Optional[str] = None
    max_pages: Optional[int] = None
    enable_rethink: bool = True
    max_rethink_times: int = 3

class PPTStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class PPTResponse(BaseModel):
    """PPT生成响应模型"""
    task_id: str
    status: PPTStatus
    progress: int  # 0-100
    current_step: str
    step_name: Optional[str] = None
    outline: Optional[str] = None
    pages: Optional[List[str]] = None
    error_message: Optional[str] = None
    thinking_content: Optional[str] = None
    content: Optional[str] = None

class FileUploadResponse(BaseModel):
    """文件上传响应模型"""
    filename: str
    file_type: str
    size: int
    content_preview: str
    success: bool
    error_message: Optional[str] = None

class ParsedPPTPage(BaseModel):
    """解析后的PPT页面模型"""
    page_num: str
    title: str
    summary: str
    body: str
    img_table_advice: str

class WebSocketMessage(BaseModel):
    """WebSocket消息模型"""
    type: str
    data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None