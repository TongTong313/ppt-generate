import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ppt_generate.agents.ppt_agent import PPTAgent
import asyncio
from typing import AsyncGenerator, Dict, Any
import json
import uuid
from models.schemas import PPTResponse, PPTStatus

class PPTGenerationService:
    """PPT生成服务"""
    
    def __init__(self):
        self.ppt_agent = PPTAgent()
        self.active_tasks = {}
    
    async def generate_ppt_stream(self, 
                                task_id: str,
                                query: str, 
                                reference_content: str = "",
                                enable_rethink: bool = True,
                                max_rethink_times: int = 3) -> AsyncGenerator[Dict[str, Any], None]:
        """流式生成PPT，返回实时进度"""
        
        try:
            # 步骤1: 生成大纲
            yield {
                "task_id": task_id,
                "status": "processing",
                "progress": 10,
                "current_step": "outline_generation",
                "step_name": "正在生成PPT大纲...",
                "thinking_content": "",
                "content": ""
            }
            
            # 调用PPTAgent生成大纲
            await self.ppt_agent.generate_ppt_outline(query, reference_content)
            
            yield {
                "task_id": task_id,
                "status": "processing",
                "progress": 40,
                "current_step": "outline_completed",
                "step_name": "大纲生成完成",
                "outline": self.ppt_agent.ppt_info["outline"]
            }
            
            # 步骤2: 生成页面内容
            yield {
                "task_id": task_id,
                "status": "processing",
                "progress": 50,
                "current_step": "content_generation",
                "step_name": "正在生成PPT内容..."
            }
            
            await self.ppt_agent.generate_page_content(
                outline=self.ppt_agent.ppt_info["outline"],
                rethink=enable_rethink,
                max_rethink_times=max_rethink_times
            )
            
            # 步骤3: 完成
            yield {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "current_step": "completed",
                "step_name": "PPT生成完成",
                "outline": self.ppt_agent.ppt_info["outline"],
                "pages": self.ppt_agent.ppt_info["pages"]
            }
            
        except Exception as e:
            yield {
                "task_id": task_id,
                "status": "error",
                "progress": 0,
                "current_step": "error",
                "step_name": "生成失败",
                "error_message": str(e)
            }
    
    async def generate_ppt_sync(self, 
                              query: str, 
                              reference_content: str = "",
                              enable_rethink: bool = True,
                              max_rethink_times: int = 3) -> Dict[str, Any]:
        """同步生成PPT"""
        task_id = str(uuid.uuid4())
        
        try:
            # 生成大纲
            await self.ppt_agent.generate_ppt_outline(query, reference_content)
            
            # 生成页面内容
            await self.ppt_agent.generate_page_content(
                outline=self.ppt_agent.ppt_info["outline"],
                rethink=enable_rethink,
                max_rethink_times=max_rethink_times
            )
            
            return {
                "task_id": task_id,
                "status": "completed",
                "progress": 100,
                "current_step": "completed",
                "outline": self.ppt_agent.ppt_info["outline"],
                "pages": self.ppt_agent.ppt_info["pages"]
            }
            
        except Exception as e:
            return {
                "task_id": task_id,
                "status": "error",
                "progress": 0,
                "current_step": "error",
                "error_message": str(e)
            }
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        return self.active_tasks.get(task_id, {
            "task_id": task_id,
            "status": "not_found",
            "error_message": "任务不存在"
        })