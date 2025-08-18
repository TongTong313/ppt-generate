from ppt_generate.agents import MCPClient
from openai import AsyncOpenAI
import os
import re
from ppt_generate.prompts.system_prompt import (
    PPT_OUTLINE_PROMPT,
    PPT_PAGE_CONTENT_PROMPT,
    PPT_PAGE_RETHINK_PROMPT,
    PPT_MODIFY_PROMPT,
    PPT_GENERATE_PROMPT,
    PPT_HTML_TEMPLATE_PROMPT,
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
            "query": "",
            "reference_content": "",
            "outline": "",
            "pages": [],
            "html": "",
        }

    # 生成PPT大纲与每页主要内容
    async def generate_ppt_outline(
        self,
        query: str,
        reference_content: Optional[str] = None,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        messages = [
            {"role": "system", "content": PPT_OUTLINE_PROMPT},
            {
                "role": "user",
                "content": f"用户需求：{query}\n参考内容：{reference_content if reference_content else '无'}",
            },
        ]
        self.ppt_info["query"] = query
        self.ppt_info["reference_content"] = reference_content

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
        print("<outline_think>")
        if on_event:
            on_event({"stage": "outline_think", "type": "start"})

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
                if on_event and not is_answering and delta.reasoning_content:
                    on_event(
                        {
                            "stage": "outline_think",
                            "type": "token",
                            "text": delta.reasoning_content,
                        }
                    )

            # 收到content，开始进行回复
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n</outline_think>\n")
                    # print("<outline_answer>")
                    is_answering = True
                    if on_event:
                        on_event({"stage": "outline_think", "type": "end"})
                        on_event({"stage": "outline_answer", "type": "start"})
                print(delta.content, end="", flush=True)
                answer_content += delta.content
                if on_event:
                    on_event(
                        {
                            "stage": "outline_answer",
                            "type": "token",
                            "text": delta.content,
                        }
                    )

        # print("\n</outline_answer>")

        # 从完整内容中提取大纲部分
        outline_match = re.search(
            r"<outline>(.*?)</outline>", answer_content, re.DOTALL
        )
        if outline_match:
            self.ppt_info["outline"] = outline_match.group(1).strip()
            if on_event:
                on_event(
                    {
                        "stage": "outline_answer",
                        "type": "end",
                    }
                )
                on_event(
                    {
                        "stage": "outline_done",
                        "outline": self.ppt_info["outline"],
                    }
                )
        else:
            raise ValueError("未能在输出中找到大纲内容，请检查模型输出格式是否正确")

    async def generate_page_content(
        self,
        outline: str,
        rethink: bool = False,
        max_rethink_times: int = 3,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        """
        根据大纲内容把每一页要包含的内容生成出来，至少需要包括一个总结句还有正文的文本内容信息，提供图像和表格添加的建议。

        Args:
            outline (str): 大纲内容，用于指导生成每一页的内容。
            rethink (bool, optional): 是否对生成的内容进行重新思考。默认值为False。
            max_rethink_times (int, optional): 重新思考的最大次数。默认值为3。
        """
        if not self.ppt_info["outline"]:
            raise ValueError("请先生成大纲")
        messages = [
            {
                "role": "system",
                "content": PPT_PAGE_CONTENT_PROMPT + "\n" + self.ppt_info["query"],
            },
            {
                "role": "user",
                "content": f"大纲内容：{outline}\n参考内容：{self.ppt_info['reference_content']}",
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
        print("\n<content_think>")
        if on_event:
            on_event({"stage": "content_think", "type": "start"})

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
                if on_event and not is_answering and delta.reasoning_content:
                    on_event(
                        {
                            "stage": "content_think",
                            "type": "token",
                            "text": delta.reasoning_content,
                        }
                    )

            # 收到content，开始进行回复
            if hasattr(delta, "content") and delta.content:
                if not is_answering:
                    print("\n</content_think>\n")
                    # print("<content_answer>")
                    is_answering = True
                    if on_event:
                        on_event({"stage": "content_think", "type": "end"})
                        on_event({"stage": "content_answer", "type": "start"})
                print(delta.content, end="", flush=True)
                answer_content += delta.content
                if on_event:
                    on_event(
                        {
                            "stage": "content_answer",
                            "type": "token",
                            "text": delta.content,
                        }
                    )

            # print("\n</content_answer>")
        # 反思过程
        if rethink:
            if on_event:
                on_event({"stage": "rethinking_begin"})
            answer_content = await self._rethinking(
                answer_content, max_rethink_times=max_rethink_times, on_event=on_event
            )

        # 把通过<page>和</page>包裹的信息解耦出来，每一页一个内容放入self.ppt_info["pages"]中
        page_content_match = re.findall(
            r"<page>(.*?)</page>", answer_content, re.DOTALL
        )
        self.ppt_info["pages"] = [page.strip() for page in page_content_match]
        if on_event:
            on_event(
                {
                    "stage": "content_answer",
                    "type": "end",
                }
            )
            on_event(
                {
                    "stage": "content_done",
                    "pages": self.ppt_info["pages"],
                }
            )

    async def _rethinking(
        self,
        page_content: str,
        reference_content: Optional[str] = None,
        max_rethink_times: Optional[int] = 3,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> str:
        """
        对生成每一页的内容进行重新思考，确保内容丰富、详细，并且符合PPT的格式要求。首先反思，反思后给出建议，然后再根据建议修改原有的PPT内容。

        Args:
            page_content (str): 要重新思考的页面内容。
            reference_content (Optional[str], optional): 参考内容，用于辅助生成内容。默认值为None。
            max_rethink_times (int, optional): 最大反思次数。默认值为3。

        Returns:
            str: 重新思考后的页面内容。

        """

        for i in range(max_rethink_times):
            # 暂定整体反思，还没有存在pages里面，所以直接提取就好了

            print("=" * 20 + "开始第" + str(i + 1) + "轮反思" + "=" * 20)

            # 1. 先反思给建议，每一轮rethink都重新生成message，防止上下文爆炸
            messages = [
                {
                    "role": "system",
                    "content": PPT_PAGE_RETHINK_PROMPT.format(
                        query=self.ppt_info["query"],
                        outline=self.ppt_info["outline"],
                        reference_content=self.ppt_info["reference_content"],
                    ),
                },
                {
                    "role": "user",
                    "content": page_content,
                },
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
            # 收集思考内容
            reasoning_content = ""
            # 收集回复内容
            answer_content = ""
            # 回复内容是否开始
            is_answering = False
            # 加一个标签
            print("\n<rethinking_think>")
            if on_event:
                on_event(
                    {
                        "stage": "rethinking_think",
                        "type": "start",
                        "round": i + 1,
                    }
                )

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
                    if on_event and not is_answering and delta.reasoning_content:
                        on_event(
                            {
                                "stage": "rethinking_think",
                                "type": "token",
                                "text": delta.reasoning_content,
                                "round": i + 1,
                            }
                        )

                if hasattr(delta, "content") and delta.content:
                    if not is_answering:
                        print("\n</rethinking_think>\n")
                        # print("<rethinking_answer>")
                        is_answering = True
                        if on_event:
                            on_event(
                                {
                                    "stage": "rethinking_think",
                                    "type": "end",
                                    "round": i + 1,
                                }
                            )
                            on_event(
                                {
                                    "stage": "rethinking_answer",
                                    "type": "start",
                                    "round": i + 1,
                                }
                            )
                    print(delta.content, end="", flush=True)
                    answer_content += delta.content
                    if on_event:
                        on_event(
                            {
                                "stage": "rethinking_answer",
                                "type": "token",
                                "text": delta.content,
                                "round": i + 1,
                            }
                        )

            # 判断输出有没有包含“检查通过”，有检查通过就跳出循环
            if "检查通过" in answer_content:
                if on_event:
                    on_event(
                        {
                            "stage": "rethinking_answer",
                            "type": "end",
                            "round": i + 1,
                        }
                    )
                    on_event(
                        {
                            "stage": "rethinking_pass",
                            "round": i + 1,
                        }
                    )
                return answer_content

            # 没有检查通过，就得按照建议修改
            messages = [
                {
                    "role": "system",
                    "content": PPT_MODIFY_PROMPT.format(
                        query=self.ppt_info["query"],
                        outline=self.ppt_info["outline"],
                        reference_content=(
                            reference_content if reference_content else ""
                        ),
                        modify_advice=answer_content,
                    ),
                },
                {
                    "role": "user",
                    "content": page_content,
                },
            ]

            # 3. 再根据建议修改内容，这里就不进行思考了
            response = await self.llm.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                tool_choice="none",
                messages=messages,
                temperature=self.temperature,
                stream=True,
            )

            # 收集回复内容
            answer_content = ""
            print("=" * 20 + "修改内容" + "=" * 20)
            if on_event:
                on_event(
                    {
                        "stage": "modify_answer",
                        "type": "start",
                        "round": i + 1,
                    }
                )

            async for chunk in response:
                if not chunk.choices:
                    print("\nUsage: ")
                    print(chunk.usage)
                    continue

                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    print(delta.content, end="", flush=True)
                    answer_content += delta.content
                    if on_event:
                        on_event(
                            {
                                "stage": "modify_answer",
                                "type": "token",
                                "text": delta.content,
                                "round": i + 1,
                            }
                        )
            # 3. 把修改后的内容赋值给page_content，然后继续下一轮循环
            page_content = answer_content
            if on_event:
                on_event(
                    {
                        "stage": "modify_answer",
                        "type": "end",
                        "round": i + 1,
                    }
                )

        return page_content

    async def generate_html(self, output_path: str = "output.html"):
        """
        根据每页的内容，采用大模型生成html格式的PPT，并保存为文件

        Args:
            output_path (str): 输出HTML文件的路径，默认为output.html
        """
        # 读取每一页的内容（数组形式，每个数组是一个json）
        page_content = self.ppt_info["pages"]
        # 先生成一个html模板
        messages = [
            {
                "role": "system",
                "content": PPT_HTML_TEMPLATE_PROMPT,
            },
            {
                "role": "user",
                "content": "用户的需求为：{}".format(self.ppt_info["query"]),
            },
        ]

        # 一页一页生成，首先前提就是要形成一个html的PPT模板，不包含任何内容
        response = await self.llm.chat.completions.create(
            model=self.model,
            max_tokens=self.max_tokens,
            tool_choice="none",
            messages=messages,
            temperature=self.temperature,
            stream=True,
        )

        answer_content = ""
        print("=" * 20 + "html模板生成" + "=" * 20)
        # 收集回复内容
        async for chunk in response:
            if not chunk.choices:
                print("\nUsage: ")
                print(chunk.usage)
                continue

            delta = chunk.choices[0].delta
            if hasattr(delta, "content") and delta.content:
                print(delta.content, end="", flush=True)
                answer_content += delta.content

        full_html = answer_content
        css_template = answer_content

        # 现在一页一页来生成html
        for page_num, page in enumerate(page_content):
            messages = [
                {
                    "role": "system",
                    "content": PPT_GENERATE_PROMPT.format(css_template=css_template),
                },
                {
                    "role": "user",
                    "content": "用户的需求为：{}，这一页的内容为：{}".format(
                        self.ppt_info["query"], page
                    ),
                },
            ]

            response = await self.llm.chat.completions.create(
                model=self.model,
                max_tokens=self.max_tokens,
                tool_choice="none",
                messages=messages,
                temperature=self.temperature,
                stream=True,
            )

            # 收集回复内容
            print("=" * 20 + "正在生成第{}页的html代码".format(page_num) + "=" * 20)

            async for chunk in response:
                if not chunk.choices:
                    print("\nUsage: ")
                    print(chunk.usage)
                    continue

                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    print(delta.content, end="", flush=True)
                    full_html += delta.content

        # 保存完整的HTML内容到文件
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(full_html)
            print(f"\nHTML文件已成功保存到: {output_path}")
            self.ppt_info["html"] = full_html
        except Exception as e:
            print(f"保存HTML文件时发生错误: {str(e)}")
            raise


async def main():
    ppt_agent = PPTAgent()
    query = "生成一个关于Python的PPT，主题内容不超过5页"
    reference_content = (
        "Python是一种高级编程语言，被广泛应用于数据分析、人工智能、Web开发等领域。"
    )
    await ppt_agent.generate_ppt_outline(query, reference_content)
    await ppt_agent.generate_page_content(
        outline=ppt_agent.ppt_info["outline"],
        rethink=True,
        max_rethink_times=1,
    )
    await ppt_agent.generate_html()

    # print("\n生成完成，完整内容为：")
    # print(ppt_agent.ppt_info["outline"])
    # print("\n每一页的内容为：")
    # print(ppt_agent.ppt_info["pages"])


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
