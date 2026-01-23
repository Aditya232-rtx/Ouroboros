import sys
from unittest.mock import MagicMock

# Mock llama_cpp before any tests run or imports happen
module_name = "llama_cpp"
if module_name not in sys.modules:
    mock_module = MagicMock()
    sys.modules[module_name] = mock_module
    # Also mock Llama class specifically
    mock_module.Llama = MagicMock()

# Mock other potential missing dependencies if needed
# e.g. pydantic_settings might be missing depending on environment
# But the error was specifically about llama_cpp
