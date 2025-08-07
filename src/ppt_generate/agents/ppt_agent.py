from ppt_generate.agents import MCPClient
from openai import AsyncOpenAI
import os
import re
from ppt_generate.prompts.system_prompt import (
    PPT_OUTLINE_PROMPT,
    PPT_PAGE_CONTENT_PROMPT,
)
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
        max_tokens: int = 8000,
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
    async def generate_ppt_outline(
        self, query: str, reference_content: Optional[str] = None
    ) -> None:
        messages = [
            {"role": "system", "content": PPT_OUTLINE_PROMPT},
            {
                "role": "user",
                "content": f"用户需求：{query}\n参考内容：{reference_content if reference_content else '无'}",
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
            extra_body={"enable_thinking": True},
        )

        # 收集思考内容
        reasoning_content = ""
        # 收集回复内容
        answer_content = ""
        # 回复内容是否开始
        is_answering = False
        # 加一个标签
        print("<think>")

        async for chunk in response:
            if not chunk.choices:
                print("\nUsage: ")
                print(chunk.usage)
                continue

            delta = chunk.choices[0].delta
            # 只收集思考内容
            if (
                hasattr(delta, "reasoning_content")
                and delta.reasoning_content is not None
            ):
                if not is_answering:
                    print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content

            # 收到content，开始进行回复
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n</think>\n")
                    print("<answer>")
                    is_answering = True
                print(delta.content, end="", flush=True)
                answer_content += delta.content

        # 从完整内容中提取大纲部分
        outline_match = re.search(
            r"<outline>(.*?)</outline>", answer_content, re.DOTALL
        )
        if outline_match:
            self.ppt_info["outline"] = outline_match.group(1).strip()
        else:
            raise ValueError("未能在输出中找到大纲内容，请检查模型输出格式是否正确")

    async def generate_page_content(
        self,
        outline: str,
        reference_content: Optional[str] = None,
        rethink: bool = False,
        max_rethink_times: int = 3,
    ) -> None:
        """
        根据大纲内容把每一页要包含的内容生成出来，至少需要包括一个总结句还有正文的文本内容信息，提供图像和表格添加的建议。

        Args:
            outline (str): 大纲内容，用于指导生成每一页的内容。
            reference_content (Optional[str], optional): 参考内容，用于辅助生成内容。默认值为None。
            rethink (bool, optional): 是否对生成的内容进行重新思考。默认值为False。
            max_rethink_times (int, optional): 重新思考的最大次数。默认值为3。
        """
        if not self.ppt_info["outline"]:
            raise ValueError("请先生成大纲")
        messages = [
            {"role": "system", "content": PPT_PAGE_CONTENT_PROMPT},
            {
                "role": "user",
                "content": f"大纲内容：{outline}\n参考内容：{reference_content if reference_content else '无'}",
            },
        ]

        # 流式输出，在这里同样不需要调用任何工具
        response = await self.llm.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.temperature,
            stream=True,
            extra_body={"enable_thinking": True},
        )

        # 收集思考内容
        reasoning_content = ""
        # 收集回复内容
        answer_content = ""
        # 回复内容是否开始
        is_answering = False
        # 加一个标签
        print("\n<think>")

        async for chunk in response:
            if not chunk.choices:
                print("\nUsage: ")
                print(chunk.usage)
                continue

            delta = chunk.choices[0].delta
            # 只收集思考内容
            if (
                hasattr(delta, "reasoning_content")
                and delta.reasoning_content is not None
            ):
                if not is_answering:
                    print(delta.reasoning_content, end="", flush=True)
                reasoning_content += delta.reasoning_content

            # 收到content，开始进行回复
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n</think>\n")
                    print("<answer>")
                    is_answering = True
                print(delta.content, end="", flush=True)
                answer_content += delta.content

        # 把通过<page>和</page>包裹的信息解耦出来，每一页一个内容放入self.ppt_info["pages"]中
        page_content_match = re.findall(
            r"<page>(.*?)</page>", answer_content, re.DOTALL
        )
        self.ppt_info["pages"] = [page.strip() for page in page_content_match]

    async def _rethinking(self, page_content: str) -> bool:
        """
        对生成每一页的内容进行重新思考，确保内容丰富、详细，并且符合PPT的格式要求。

        Args:
            page_content (str): 要重新思考的页面内容。

        Returns:
            bool: 大模型是否觉得本次反思结果达到要求，True表示达到要求，False表示未达到要求。
        """
        messages = [
            {"role": "system", "content": PPT_PAGE_RETHINK_PROMPT},
            {"role": "user", "content": page_content},
        ]
        response = await self.llm.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.temperature,
            stream=True,
            extra_body={"enable_thinking": True},
        )
        full_content = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                # 信息存储
                full_content += chunk.choices[0].delta.content
                print(chunk.choices[0].delta.content, end="", flush=True)
        return full_content


async def main():
    ppt_agent = PPTAgent()
    query = "生成一个关于Python的PPT"
    reference_content = (
        "Python是一种高级编程语言，被广泛应用于数据分析、人工智能、Web开发等领域。"
    )
    await ppt_agent.generate_ppt_outline(query, reference_content)
    await ppt_agent.generate_page_content(
        ppt_agent.ppt_info["outline"], reference_content
    )
    # print("\n生成完成，完整内容为：")
    # print(ppt_agent.ppt_info["outline"])
    # print("\n每一页的内容为：")
    # print(ppt_agent.ppt_info["pages"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
