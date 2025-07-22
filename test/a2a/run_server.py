from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from coding_agent import CodingAgentExecutor, CodingAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
import os
from a2a.server.tasks import (
    InMemoryTaskStore,
)
import uvicorn

if __name__ == "__main__":

    # 说明智能体的技能
    skill = AgentSkill(
        id="88",
        name="coding agent",
        description="编代码的智能体",
        tags=["编码", "代码", "coding"],
        examples=["编写一个hello world程序", "编写一个快速排序的python程序"],
    )

    # 构建AgentCard，也即智能体的名片
    coding_agent_card = AgentCard(
        name="代码智能体",
        description="编写代码的智能体",
        url="http://localhost:9999/",
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        version="1.0.0",
    )

    # 算法代码要被client调用，得用A2A的DefaultRequestHandler封装一下，让它可以应对来自client的请求，并自动执行CodingAgentExecutor中的对应函数
    request_handler = DefaultRequestHandler(
        agent_executor=CodingAgentExecutor(
            agent=CodingAgent(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        ),
        task_store=InMemoryTaskStore(),
    )

    # 使用A2A SDK封装一个应用服务
    # Starlette框架简介
    # Starlette是一个轻量级的ASGI（异步服务器网关接口）框架/工具包，专为使用Python构建异步Web服务而设计。它既可以作为一个完整的框架使用，也可以作为ASGI工具包使用，其组件可以独立使用。
    server = A2AStarletteApplication(
        agent_card=coding_agent_card,
        http_handler=request_handler,
    )

    # 起服务
    uvicorn.run(server.build(), host="0.0.0.0", port=9999)
