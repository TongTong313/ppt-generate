from typing import Callable, Dict, Any, Type, Literal, Union, List
from typing import get_type_hints, get_origin, get_args
import inspect
from mcp.server.fastmcp import FastMCP

# from ppt_generate.tool.tool import pdf_to_text


class MCPServer:
    """MCPServer类，目标就是将一组函数封装成MCP Server，还要满足OpenAI接口的规范"""

    def __init__(
        self,
        *,
        funcs: List[Callable],
        server_name: str = "mcp_server",
        host: str = "127.0.0.1",
        port: int = 8888,
    ):
        # 搞个工具字典，key是工具名，value是工具函数，方便后面访问到函数
        self.tool_schemas: Dict[str, Dict[str, Any]] = {}
        self.mcp_server = FastMCP(name=server_name, host=host, port=port)

        # 添加工具
        for func in funcs:
            self.mcp_server.add_tool(
                fn=func,
                name=func.__name__,
                description=self._get_tool_description(func),
            )

    def run(
        self,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        mount_path: str | None = None,
    ):
        self.mcp_server.run(transport, mount_path)

    def _get_tool_description(self, func: Callable) -> str:
        """按照不同注释风格，Google和Numpy风格，都要能提取tool_description

        Args:
            func (Callable): 函数对象

        Returns:
            str: 工具描述
        """
        if not func.__doc__:
            return ""

        doc = func.__doc__

        # 处理Google风格文档
        if "Args:" in doc:
            # 取Args:之前的内容作为描述
            description = doc.split("Args:")[0].strip()
            return description

        # 处理NumPy风格文档
        if "Parameters" in doc:
            # 取Parameters之前的内容作为描述
            description = doc.split("Parameters")[0].strip()
            return description

        # 如果都不是，就取第一行作为描述
        return doc.split("\n")[0].strip()
