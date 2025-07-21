import logging
import httpx
from typing import Dict, Any
from uuid import uuid4
from a2a.types import AgentCard, Message, TextPart
from a2a.client import A2AClient, A2ACardResolver
from a2a.types import SendMessageRequest, MessageSendParams, SendStreamingMessageRequest


async def main() -> None:
    PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"

    # 设置一个logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # 获得logger实例

    # 获取服务端的url
    base_url = "http://localhost:9999"

    # 获取agent card并初始化一个client
    async with httpx.AsyncClient() as httpx_client:
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=base_url)

        final_agent_card_to_use: AgentCard | None = None

        try:
            logger.info(f"尝试获取agent card，url为{base_url}{PUBLIC_AGENT_CARD_PATH}")
            final_agent_card_to_use = await resolver.get_agent_card()

            logger.info(f"已成功获取agent card：")
            logger.info(
                f"{final_agent_card_to_use.model_dump_json(indent=2, exclude_none=True)}"
            )

            logger.info(f"使用该agent card初始化client")

        except Exception as e:
            logger.error(f"获取agent card失败，错误信息为：{e}")
            raise RuntimeError(f"获取agent card失败，无法继续运行") from e

        # 初始化client
        try:
            logger.info(f"尝试初始化client")
            client = A2AClient(
                httpx_client=httpx_client, agent_card=final_agent_card_to_use
            )
            logger.info(f"已成功初始化client")
        except Exception as e:
            logger.error(f"初始化client失败，错误信息为：{e}")
            raise RuntimeError(f"初始化client失败，无法继续运行") from e

        # send_message_payload: Dict[str, Any] = {
        #     "message": {
        #         "role": "user",
        #         "parts": [{"kind": "text", "text": "帮我写一段快速排序代码"}],
        #         "messageId": uuid4().hex,
        #     },
        # }

        send_message_payload: Message = Message(
            role="user",
            parts=[TextPart(text="帮我写一段快速排序代码")],
            messageId=uuid4().hex,
        )

        # 都是pydantic模型
        # 非流式请求
        # request = SendMessageRequest(
        #     id=str(uuid4()), params=MessageSendParams(**send_message_payload)
        # )
        # print(f"非流式请求：{request}")

        # response = await client.send_message(request)
        # print(response.model_dump(mode="json", exclude_none=True))

        # 流式请求
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), params=MessageSendParams(message=send_message_payload)
        )

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            # print(chunk.model_dump(mode="json", exclude_none=True))
            print(chunk)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
