from a2a.types import AgentCard, AgentSkill, AgentCapabilities

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
        url="http://localhost:8765/",
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        version="1.0.0",
    )

    print(type(skill))
    print(type(coding_agent_card))
