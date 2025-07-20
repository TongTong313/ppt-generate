from email import message
from a2a.server.agent_execution import AgentExecutor
from openai import AsyncOpenAI
from typing import Literal, Optional, List
import os
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils import new_agent_text_message


class CodingAgent:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str = "qwen-plus",
        tool_choice: Literal["auto", "required", "none"] = "auto",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False,
        enable_thinking: Optional[bool] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.stream = stream
        self.enable_thinking = enable_thinking
        self.tool_choice = tool_choice

        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )

    async def invoke(self, messages: List[dict[str, str]]) -> str:
        system_prompt = [
            {
                "role": "system",
                "content": "你是一个代码助手，根据用户的输入，生成对应的代码。注意你只能写代码，遇到不是代码的问题需要你反问用户，让用户明确需求",
            }
        ]
        messages = system_prompt + messages

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=self.stream,
            tool_choice=self.tool_choice,
        )
        return response.choices[0].message.content


class CodingAgentExecutor(AgentExecutor):
    def __init__(self, agent: CodingAgent) -> None:
        self.agent = agent

    # 必须实现execute和cancel方法
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:

        message = {
            "role": "user" if context.message.role == "user" else "assistant",
            "content": context.message.parts[0].root.text,
        }
        messages = [message]

        response = await self.agent.invoke(messages)
        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("cancel not supported")


if __name__ == "__main__":
    import asyncio

    async def main():
        coding_agent = CodingAgent(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )

        # 测试案例
        result = await coding_agent.invoke(
            [
                {
                    "role": "user",
                    "content": "写一个快速排序算法",
                }
            ]
        )
        print(result)

    asyncio.run(main())
