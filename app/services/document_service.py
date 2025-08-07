from typing import Dict, Any, List
import aiofiles
from pathlib import Path
import os
from fastapi import UploadFile
import asyncio

# 文档处理库
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    import docx
except ImportError:
    docx = None

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

class DocumentProcessor:
    """支持多种文档格式的处理器"""
    
    SUPPORTED_FORMATS = {
        '.pdf': 'extract_pdf',
        '.docx': 'extract_docx', 
        '.doc': 'extract_doc',
        '.txt': 'extract_txt',
        '.md': 'extract_markdown',
        '.xlsx': 'extract_excel',
        '.csv': 'extract_csv',
        '.html': 'extract_html'
    }
    
    def __init__(self):
        # 确保临时目录存在
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)
    
    async def process_file(self, file: UploadFile) -> Dict[str, Any]:
        """处理上传的文件并提取文本内容"""
        file_extension = Path(file.filename).suffix.lower()
        
        if file_extension not in self.SUPPORTED_FORMATS:
            raise ValueError(f"不支持的文件格式: {file_extension}")
            
        # 保存临时文件
        temp_path = self.temp_dir / file.filename
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        try:
            # 提取文本
            extractor_method = getattr(self, self.SUPPORTED_FORMATS[file_extension])
            extracted_content = await extractor_method(str(temp_path))
            
            return {
                "filename": file.filename,
                "file_type": file_extension,
                "content": extracted_content,
                "size": len(content)
            }
        finally:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
    
    async def extract_pdf(self, file_path: str) -> str:
        """提取PDF文件内容"""
        if PyPDF2 is None:
            raise ImportError("请安装PyPDF2库: pip install PyPDF2")
        
        def _extract():
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
        
        return await asyncio.get_event_loop().run_in_executor(None, _extract)
    
    async def extract_docx(self, file_path: str) -> str:
        """提取Word文档内容"""
        if docx is None:
            raise ImportError("请安装python-docx库: pip install python-docx")
        
        def _extract():
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        
        return await asyncio.get_event_loop().run_in_executor(None, _extract)
    
    async def extract_doc(self, file_path: str) -> str:
        """提取旧版Word文档内容"""
        # 对于.doc文件，建议用户转换为.docx格式
        raise ValueError("请将.doc文件转换为.docx格式后重新上传")
    
    async def extract_txt(self, file_path: str) -> str:
        """提取文本文件内容"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def extract_markdown(self, file_path: str) -> str:
        """提取Markdown文件内容"""
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            return await f.read()
    
    async def extract_excel(self, file_path: str) -> str:
        """提取Excel文件内容"""
        if pd is None:
            raise ImportError("请安装pandas库: pip install pandas openpyxl")
        
        def _extract():
            df = pd.read_excel(file_path)
            return df.to_string()
        
        return await asyncio.get_event_loop().run_in_executor(None, _extract)
    
    async def extract_csv(self, file_path: str) -> str:
        """提取CSV文件内容"""
        if pd is None:
            raise ImportError("请安装pandas库: pip install pandas")
        
        def _extract():
            df = pd.read_csv(file_path)
            return df.to_string()
        
        return await asyncio.get_event_loop().run_in_executor(None, _extract)
    
    async def extract_html(self, file_path: str) -> str:
        """提取HTML文件内容"""
        if BeautifulSoup is None:
            raise ImportError("请安装beautifulsoup4库: pip install beautifulsoup4")
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            html_content = await f.read()
        
        def _extract():
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup.get_text()
        
        return await asyncio.get_event_loop().run_in_executor(None, _extract)