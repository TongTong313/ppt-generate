import logging
import httpx
from typing import Dict, Any, AsyncIterator
from uuid import uuid4
from a2a.types import AgentCard, Message, TextPart
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams, SendStreamingMessageRequest


# 入口（主控&规划）智能体，将任务发给其他智能体搞定
class EntryAgent:
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)  # 获得logger实例

    async def invoke(self, base_url: str, prompt: str) -> AsyncIterator[Dict[str, Any]]:
        """
        调用该智能体，通过A2A协议与server智能体进行交互

        Args:
            base_url (str): server智能体的url
            prompt (str): 智能体的输入提示

        Returns:
            AsyncIterator[Dict[str, Any]]: server智能体的响应流
        """

        async with httpx.AsyncClient() as httpx_client:
            # 获取agent card
            resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

            final_agent_card_to_use: AgentCard | None = None

            try:
                self.logger.info(
                    f"尝试获取agent card，url为{base_url}{resolver.agent_card_path}"
                )
                final_agent_card_to_use = await resolver.get_agent_card()

                self.logger.info(f"已成功获取agent card：")
                self.logger.info(
                    f"{final_agent_card_to_use.model_dump_json(indent=2, exclude_none=True)}"
                )

                self.logger.info(f"使用该agent card初始化client")

            except Exception as e:
                self.logger.error(f"获取agent card失败，错误信息为：{e}")
                raise RuntimeError(f"获取agent card失败，无法继续运行") from e

            # 初始化client
            try:
                self.logger.info(f"尝试初始化client")
                client = A2AClient(
                    httpx_client=httpx_client, agent_card=final_agent_card_to_use
                )
                self.logger.info(f"已成功初始化client")
            except Exception as e:
                self.logger.error(f"初始化client失败，错误信息为：{e}")
                raise RuntimeError(f"初始化client失败，无法继续运行") from e

            # A2A协议规定的标准Message数据格式
            send_message_payload: Message = Message(
                role="user",
                parts=[TextPart(text=prompt)],
                message_id=uuid4().hex,
            )

            # 流式请求：使用A2A SDK封装好的SendStreamingMessageRequest
            streaming_request = SendStreamingMessageRequest(
                id=str(uuid4()), params=MessageSendParams(message=send_message_payload)
            )

            stream_response = client.send_message_streaming(streaming_request)

            async for chunk in stream_response:
                # print(chunk.model_dump(mode="json", exclude_none=True))
                yield chunk
