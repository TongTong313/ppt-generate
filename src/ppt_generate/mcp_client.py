from mcp.client.streamable_http import streamablehttp_client
from mcp import ClientSession
import asyncio
from typing import Optional
from contextlib import AsyncExitStack
from openai import AsyncOpenAI
import os


class MCPClient:
    """MCP Client for interacting with an MCP Streamable HTTP server"""

    def __init__(
            self,
            api_key: str = os.getenv("DASHSCOPE_API_KEY", ""),
            base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm_cli = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def connect_to_streamable_http_server(self,
                                                server_url: str,
                                                headers: Optional[dict] = None
                                                ):
        """Connect to an MCP server running with HTTP Streamable transport"""
        self._streams_context = streamablehttp_client(
            url=server_url,
            headers=headers or {},
        )
        read_stream, write_stream, _ = await self._streams_context.__aenter__()

        self._session_context = ClientSession(read_stream, write_stream)
        self.session: ClientSession = await self._session_context.__aenter__()

        await self.session.initialize()

    async def process_query(self, query: str) -> str:
        """Process a query using OpenAI and available tools"""
        messages = [{"role": "user", "content": query}]

        response = await self.session.list_tools()
        # print(response)
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            }
        } for tool in response.tools]
        print(available_tools)

        # Initial OpenAI API call
        response = await self.llm_cli.chat.completions.create(
            model="qwen-plus",
            max_tokens=1000,
            messages=messages,
            tools=available_tools,
        )
        print(response)

        # # Process response and handle tool calls
        # final_text = []

        # for content in response.content:
        #     if content.type == "text":
        #         final_text.append(content.text)
        #     elif content.type == "tool_use":
        #         tool_name = content.name
        #         tool_args = content.input

        #         # Execute tool call
        #         result = await self.session.call_tool(tool_name, tool_args)
        #         final_text.append(
        #             f"[Calling tool {tool_name} with args {tool_args}]")

        #         # Continue conversation with tool results
        #         if hasattr(content, "text") and content.text:
        #             messages.append({
        #                 "role": "assistant",
        #                 "content": content.text
        #             })
        #         messages.append({"role": "user", "content": result.content})

        #         # Get next response from Claude
        #         response = self.anthropic.messages.create(
        #             model="claude-3-5-sonnet-20241022",
        #             max_tokens=1000,
        #             messages=messages,
        #         )

        #         final_text.append(response.content[0].text)

        # return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Properly clean up the session and streams"""
        if self._session_context:
            await self._session_context.__aexit__(None, None, None)
        if self._streams_context:  # pylint: disable=W0125
            await self._streams_context.__aexit__(None, None, None)


async def main():
    client = MCPClient()

    try:
        await client.connect_to_streamable_http_server(
            f"http://127.0.0.1:8888/mcp")
        await client.chat_loop()
    except Exception as e:
        print(f"Error: {str(e)}")
    # finally:
    #     print("MCP Client Stopped!")
    #     await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
