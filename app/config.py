import os
from pathlib import Path

class Settings:
    """应用配置"""
    
    # 应用基本配置
    APP_NAME: str = "PPT生成系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # 服务器配置
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # 文件上传配置
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: Path = Path("uploads")
    TEMP_DIR: Path = Path("temp")
    
    # AI模型配置
    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY", "")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "qwen-plus")
    
    # PPT生成配置
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 8000
    DEFAULT_MAX_RETHINK_TIMES: int = 3
    
    def __init__(self):
        # 确保必要的目录存在
        self.UPLOAD_DIR.mkdir(exist_ok=True)
        self.TEMP_DIR.mkdir(exist_ok=True)

settings = Settings()