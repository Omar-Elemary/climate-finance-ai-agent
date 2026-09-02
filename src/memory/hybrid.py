from typing import List, Dict, Any

class AgentMemory:
    """Hybrid memory mechanism maintaining conversation history and structured facts."""
    
    def __init__(self, max_history: int = 10):
        self.conversation_history: List[Dict[str, str]] = []
        self.structured_store: Dict[str, Any] = {}
        self.max_history = max_history

    def add_interaction(self, role: str, content: str) -> None:
        """Appends a message to the conversation history, enforcing a sliding window."""
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > (self.max_history * 2):
            self.conversation_history = self.conversation_history[-self.max_history * 2:]

    def store_fact(self, key: str, value: Any) -> None:
        """Stores a structured piece of information explicitly."""
        self.structured_store[key] = value

    def get_fact(self, key: str) -> Any:
        """Retrieves a specific structured fact."""
        return self.structured_store.get(key)

    def get_full_context(self) -> Dict[str, Any]:
        """Returns both conversation history and structured memory for prompt construction."""
        return {
            "history": self.conversation_history,
            "structured_memory": self.structured_store
        }