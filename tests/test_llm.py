from src.agent.llm_service import LLMService

llm = LLMService()
print(llm.generate("Test message: say hello in one sentence."))
