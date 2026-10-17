import time
import uuid
from typing import Dict, Any, List, Optional


class ChatSession:
    """Quản lý trạng thái và lịch sử hội thoại nhiều lượt cho một phiên chat"""

    def __init__(self, session_id: str):
        self.session_id: str = session_id
        self.created_at: float = time.time()
        self.updated_at: float = time.time()
        self.turns: List[Dict[str, Any]] = []
        self.last_sku: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.product_history: List[str] = []

    def add_turn(
        self,
        user_msg: str,
        assistant_msg: str,
        intent: Optional[str] = None,
        decision: Optional[str] = None,
        skus: Optional[List[str]] = None,
        citations: Optional[List[Any]] = None
    ) -> None:
        turn_data = {
            "user_msg": user_msg,
            "assistant_msg": assistant_msg,
            "intent": intent,
            "decision": decision,
            "skus": skus or [],
            "citations": citations or [],
            "timestamp": time.time()
        }
        self.turns.append(turn_data)
        self.updated_at = time.time()

        if skus:
            # Lưu SKU gần nhất được thảo luận
            self.last_sku = skus[0]
            for s in skus:
                if s not in self.product_history:
                    self.product_history.append(s)

        if intent:
            self.last_intent = intent

    def get_context_summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turns_count": len(self.turns),
            "last_sku": self.last_sku,
            "last_intent": self.last_intent,
            "product_history": self.product_history,
            "updated_at": self.updated_at
        }


class SessionManager:
    """Quản lý danh sách các phiên chat in-memory"""

    def __init__(self):
        self._sessions: Dict[str, ChatSession] = {}

    def get_or_create(self, session_id: Optional[str] = None) -> ChatSession:
        if not session_id or not str(session_id).strip():
            session_id = f"sess-{uuid.uuid4().hex[:12]}"
        else:
            session_id = str(session_id).strip()

        if session_id not in self._sessions:
            self._sessions[session_id] = ChatSession(session_id)
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        return self._sessions.get(session_id)

    def clear_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


_global_session_manager = SessionManager()

def get_session_manager() -> SessionManager:
    return _global_session_manager
