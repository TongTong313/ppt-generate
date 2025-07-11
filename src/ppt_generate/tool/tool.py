# 构建必要的MCP工具，供Cursor或Langgraph智能体使用

import os
import logging
import re
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
import PyPDF2
import pdfplumber
import sympy
from sympy import symbols, simplify, latex
from datetime import datetime


async def pdf_to_text(pdf_path: str,
                      start_page: Optional[int] = None,
                      end_page: Optional[int] = None) -> Dict[str, Any]:
    """
    将PDF文件转换为文本
    
    Args:
        pdf_path (str): PDF文件的路径
        start_page (Optional[int]): 开始页码（从1开始，包含）
        end_page (Optional[int]): 结束页码（包含）
    
    Returns:
        Dict[str, Any]: 包含转换结果的字典
        {
            "success": bool,
            "text": str,
            "total_pages": int,
            "pages_processed": int,
            "error": str (如果失败)
        }
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(pdf_path):
            return {
                "success": False,
                "text": "",
                "total_pages": 0,
                "pages_processed": 0,
                "error": f"PDF文件不存在: {pdf_path}"
            }

        # 打开PDF文件
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            # 设置页码范围
            if start_page is None:
                start_page = 1
            if end_page is None:
                end_page = total_pages

            # 验证页码范围
            if start_page < 1 or end_page > total_pages or start_page > end_page:
                return {
                    "success": False,
                    "text": "",
                    "total_pages": total_pages,
                    "pages_processed": 0,
                    "error":
                    f"页码范围无效: {start_page}-{end_page}，总页数: {total_pages}"
                }

            # 提取文本
            extracted_text = []
            pages_processed = 0

            for page_num in range(start_page - 1, end_page):  # PyPDF2使用0基索引
                try:
                    page = pdf_reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text.strip():  # 只添加非空页面
                        extracted_text.append(
                            f"=== 第 {page_num + 1} 页 ===\n{page_text}")
                        pages_processed += 1
                except Exception as e:
                    logging.warning(f"提取第 {page_num + 1} 页时出错: {str(e)}")
                    continue

            full_text = "\n\n".join(extracted_text)

            return {
                "success": True,
                "text": full_text,
                "total_pages": total_pages,
                "pages_processed": pages_processed,
                "error": None
            }

    except Exception as e:
        return {
            "success": False,
            "text": "",
            "total_pages": 0,
            "pages_processed": 0,
            "error": f"处理PDF文件时出错: {str(e)}"
        }


async def get_current_time() -> str:
    """
    获取当前时间, 格式为: 2025-07-11 10:00:00
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
