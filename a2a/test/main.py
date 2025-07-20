from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from server import CodingAgentExecutor, CodingAgent
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
import os
from a2a.server.tasks import InMemoryTaskStore
import uvicorn

if __name__ == "__main__":
    skill = AgentSkill(
        id="88",
        name="coding agent",
        description="编代码的智能体",
        tags=["编码", "代码", "coding"],
        examples=["编写一个hello world程序", "编写一个python程序"],
    )

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

    request_handler = DefaultRequestHandler(
        agent_executor=CodingAgentExecutor(
            agent=CodingAgent(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        ),
        task_store=InMemoryTaskStore(),
    )

    server = A2AStarletteApplication(
        agent_card=coding_agent_card,
        http_handler=request_handler,
    )

    uvicorn.run(server.build(), host="0.0.0.0", port=9999)
