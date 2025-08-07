#!/usr/bin/env python3
"""PPT生成系统启动脚本"""

import uvicorn
from config import settings

def main():
    """启动应用"""
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if not settings.DEBUG else "debug"
    )

if __name__ == "__main__":
    main()