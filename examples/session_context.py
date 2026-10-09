from agent_memory_kit import Message, Scope, SessionMemory

from contextkit import ContextCompiler, ContextManager
from contextkit.adapters import InMemoryStore

scope = Scope("demo", "user-1")
sessions = SessionMemory()
sessions.append(scope, "chat-1", Message("m1", "user", "Plan dinner"))
# Character counting demonstrates the interface. Supply a model tokenizer for token budgets.
manager = ContextManager(ContextCompiler(InMemoryStore()), sessions, count_tokens=len)
context = manager.build(
    scope, session_id="chat-1", query="Suggest a menu", max_tokens=2000, reserved_tokens=300
)
print(context.render())
