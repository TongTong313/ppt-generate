from entry_agent import EntryAgent
import asyncio


async def main():
    base_url = "http://localhost:9999"
    entry_agent = EntryAgent()

    async for chunk in entry_agent.invoke(
        base_url, prompt="帮我写一个python的两数求和函数"
    ):
        print(chunk.model_dump_json())


if __name__ == "__main__":

    asyncio.run(main())
