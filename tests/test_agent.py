from unittest.mock import MagicMock
from src.llm.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    provider_name = "mock"

    def __init__(self, response_text: str = "Mock response"):
        super().__init__(api_key="test-key", model="mock-model")
        self._response_text = response_text
        self.call_count = 0
        self.last_messages = None

    def generate(self, messages: list[dict[str, str]], **kwargs) -> LLMResponse:
        self.call_count += 1
        self.last_messages = messages
        return LLMResponse(
            text=self._response_text,
            provider=self.provider_name,
            model=self.model,
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )


def test_agent_init():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Test", description="A test persona")
    llm = MockLLMProvider()
    agent = Agent(persona=persona, llm=llm)

    assert agent.persona.name == "Test"
    assert agent.llm.provider_name == "mock"
    assert agent.tools == []
    assert agent.memory is None


def test_agent_respond():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Test", description="A test persona")
    llm = MockLLMProvider(response_text="Hello from mock")
    agent = Agent(persona=persona, llm=llm)

    response = agent.respond("What is climate finance?")

    assert response == "Hello from mock"
    assert llm.call_count == 1
    assert llm.last_messages is not None
    assert any("What is climate finance?" in m["content"] for m in llm.last_messages)


def test_agent_works_without_memory():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Test")
    llm = MockLLMProvider()
    agent = Agent(persona=persona, llm=llm)

    assert agent.memory is None
    response = agent.respond("test")
    assert response == "Mock response"


def test_agent_works_with_mock_memory():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Test")
    llm = MockLLMProvider()
    memory = MagicMock()
    memory.get_context.return_value = "Previous conversation context"
    agent = Agent(persona=persona, llm=llm, memory=memory)

    response = agent.respond("Hello")

    assert response == "Mock response"
    memory.get_context.assert_called_once()
    memory.add.assert_any_call("user", "Hello")
    memory.add.assert_any_call("assistant", "Mock response")


def test_generate_opinion_returns_structured_output():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Investor", description="Climate investor")
    llm = MockLLMProvider(response_text="I believe adaptation finance should increase.")
    agent = Agent(persona=persona, llm=llm)

    result = agent.generate_opinion("Should adaptation finance increase?")

    assert isinstance(result, dict)
    assert result["topic"] == "Should adaptation finance increase?"
    assert result["persona"] == "Investor"
    assert result["opinion"] == "I believe adaptation finance should increase."
    assert isinstance(result["evidence"], list)
    assert isinstance(result["sources"], list)
    assert result["provider"] == "mock"
    assert result["model"] == "mock-model"


def test_agent_with_tool():
    from src.agent import Agent
    from src.personas.base import Persona
    from src.tools.base import Tool, ToolResult

    class MockTool(Tool):
        name = "mock_tool"
        description = "A mock tool for testing"

        def run(self, **kwargs) -> ToolResult:
            return ToolResult(success=True, data=[{"result": "test"}])

    persona = Persona(name="Test")
    llm = MockLLMProvider()
    tool = MockTool()
    agent = Agent(persona=persona, llm=llm, tools=[tool])

    assert "mock_tool" in agent._tool_map
    result = agent._use_tool("mock_tool")
    assert result.success
    assert result.data == [{"result": "test"}]


def test_agent_unknown_tool():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(name="Test")
    llm = MockLLMProvider()
    agent = Agent(persona=persona, llm=llm)

    result = agent._use_tool("nonexistent_tool")
    assert not result.success
    assert "not available" in result.error


def test_agent_system_message_contains_persona():
    from src.agent import Agent
    from src.personas.base import Persona

    persona = Persona(
        name="Investor",
        description="Climate finance expert",
        system_prompt="Focus on ROI",
        tone="analytical",
        focus_areas=["ROI", "risk"],
    )
    llm = MockLLMProvider()
    agent = Agent(persona=persona, llm=llm)

    agent.respond("test question")

    messages = llm.last_messages
    system_msg = messages[0]["content"]
    assert "Investor" in system_msg
    assert "Climate finance expert" in system_msg
    assert "Focus on ROI" in system_msg
    assert "analytical" in system_msg
    assert "ROI" in system_msg
