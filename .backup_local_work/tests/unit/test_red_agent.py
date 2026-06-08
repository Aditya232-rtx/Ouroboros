import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from src.agents.red_agent import RedAgent, RedAgentInput, RedAgentTarget

@pytest.fixture
def mock_settings():
    with patch("src.agents.red_agent.settings") as mock:
        mock.RED_AGENT_MODEL = "mock_model.gguf"
        yield mock

@pytest.fixture
def red_agent(mock_settings):
    # Mock LLM loader to avoid actual model loading
    with patch("src.agents.base_agent.Llama"):
        agent = RedAgent(model_path="mock_path")
        agent.llm = MagicMock() # Mock the LLM instance
        return agent

def test_validate_input_valid(red_agent):
    data = {
        "target": {
            "repo": "https://github.com/owner/repo",
            "branch": "develop"
        },
        "config": {
            "scanning_tools": ["semgrep"]
        }
    }
    validated = red_agent.validate_input(data)
    assert isinstance(validated, RedAgentInput)
    assert validated.target.repo == "https://github.com/owner/repo"
    assert validated.config.scanning_tools == ["semgrep"]

def test_validate_input_invalid_missing_repo(red_agent):
    data = {"config": {}}
    with pytest.raises(ValueError):
        red_agent.validate_input(data)

@pytest.mark.asyncio
async def test_execute_flow(red_agent):
    input_data = RedAgentInput(
        target=RedAgentTarget(repo="/tmp/mock_repo"),
        config=None
    )

    # Mock PyRIT Orchestrator
    mock_findings = [
        {
            "tool": "semgrep",
            "type": "python.lang.security.audit.eval-usage",
            "severity": "HIGH",
            "location": {"file": "app.py", "line": 10},
            "description": "Eval usage detected",
            "metadata": {}
        }
    ]
    
    with patch("src.agents.red_agent.PyRITOrchestrator") as MockOrch:
        instance = MockOrch.return_value
        instance.run_scan = AsyncMock(return_value=mock_findings)
        
        # Inject the mock orchestrator
        red_agent.orchestrator = instance
        
        # Mock LLM response
        red_agent.llm.create_completion.return_value = {
            "choices": [{"text": "print('POC')"}]
        }

        result = await red_agent._execute_async(input_data)
        
        assert result["scan_id"] is not None
        assert len(result["vulnerabilities"]) == 1
        assert result["vulnerabilities"][0]["type"] == "python.lang.security.audit.eval-usage"
        # Check LLM enrichment
        assert "print('POC')" in result["vulnerabilities"][0]["poc_code"]
