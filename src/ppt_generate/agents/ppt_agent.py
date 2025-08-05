from ppt_generate.agents import MCPClient
from openai import AsyncOpenAI
import os
import re
from ppt_generate.prompts.system_prompt import PPT_OUTLINE_PROMPT
from typing import List, Dict, Any, Callable, Literal, Optional, AsyncIterable


class PPTAgent(MCPClient):
    """
    PPTAgent是一个基于MCP协议的PPT生成智能体，它可以根据用户需求结合上传文本信息生成PPT。大致流程：
    1. 形成PPT大纲，明确生成PPT的页数和每一页的内容。
    2. 生成每一页PPT的内容，包括标题、内容、图片等。
    3. 生成PPT文件，保存到指定路径。（逐步研发，首先html再转为Pdf，再转为ppt）

    说明：默认支持流式输出

    Args:
        api_key (str, optional): DashScope API密钥。默认从环境变量中获取。
        base_url (str, optional): DashScope API基础URL。默认值为"https://dashscope.aliyuncs.com/compatible-mode/v1"。
        model (str, optional): 用于生成PPT的模型名称。默认值为"qwen-plus"。
        temperature (float, optional): 生成文本的温度参数。默认值为0.7。
        max_tokens (int, optional): 生成文本的最大token数。默认值为1000。

    Attributes:
        ppt_info (Dict[str, Any]): 存储PPT信息的字典，包含大纲和每页内容。
    """

    def __init__(
        self,
        api_key: str = os.getenv("DASHSCOPE_API_KEY", ""),
        base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
        model: str = "qwen-plus",
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> None:
        self.api_key: str = api_key
        self.base_url: str = base_url
        self.model: str = model
        self.temperature: float = temperature
        self.max_tokens: int = max_tokens
        self.llm = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        # 存储PPT信息
        self.ppt_info: Dict[str, Any] = {
            "outline": "",
            "pages": [],
        }

    # 生成PPT大纲与每页主要内容
    async def generate_ppt_outline(self, query: str, reference_content: str) -> None:
        messages = [
            {"role": "system", "content": PPT_OUTLINE_PROMPT},
            {
                "role": "user",
                "content": f"用户需求：{query}\n参考内容：{reference_content}",
            },
        ]

        # 流式输出，这个大模型不需要任何工具读取加载，直接流式输出即可
        response = await self.llm.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.temperature,
            stream=True,
        )
        full_content = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                # 信息存储
                full_content += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)

        # 从完整内容中提取大纲部分
        outline_match = re.search(r"<outline>(.*?)</outline>", full_content, re.DOTALL)
        if outline_match:
            self.ppt_info["outline"] = outline_match.group(1).strip()
        else:
            raise ValueError("未能在输出中找到大纲内容，请检查模型输出格式是否正确")


async def main():
    ppt_agent = PPTAgent()
    query = "生成一个关于Python的PPT"
    reference_content = (
        "Python是一种高级编程语言，被广泛应用于数据分析、人工智能、Web开发等领域。"
    )
    await ppt_agent.generate_ppt_outline(query, reference_content)
    print("\n生成完成，完整内容为：")
    print(ppt_agent.ppt_info["outline"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
