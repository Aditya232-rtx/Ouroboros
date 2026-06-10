from langchain_community.llms import LlamaCpp
from langchain_ollama import OllamaLLM

print("Testing Ollama connection...")
try:
    llm = OllamaLLM(model="ouroboros-red")
    resp = llm.invoke("Say 'hello world'")
    print(f"Response: {resp}")
except Exception as e:
    print(f"Error: {e}")
