import asyncio
from ppt_generate.tool.tool import pdf_to_text, get_current_time
from ppt_generate.tool.mcp_server import MCPServer


import multiprocessing
from ppt_generate.tool.tool import pdf_to_text, get_current_time
from ppt_generate.tool.mcp_server import MCPServer


def run_server(funcs, port):
    """在单独进程中运行服务器"""
    server = MCPServer(funcs=funcs, host="0.0.0.0", port=port)
    server.run(transport="streamable-http", mount_path="/mcp")


def main():
    # 创建进程
    process1 = multiprocessing.Process(target=run_server, args=([pdf_to_text], 8888))
    process2 = multiprocessing.Process(
        target=run_server, args=([get_current_time], 8889)
    )

    # 启动进程
    process1.start()
    process2.start()

    # 等待进程结束
    process1.join()
    process2.join()


if __name__ == "__main__":
    main()
