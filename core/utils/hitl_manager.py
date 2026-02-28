import uuid
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
from core.utils.bot_logger import get_logger

logger = get_logger("hitl_manager")

class HITLManager:
    """
    Manages Human-in-the-Loop approvals for sensitive operations.
    """
    def __init__(self):
        self.pending_approvals: Dict[str, Dict[str, Any]] = {}

    def request_approval(self, action_type: str, details: str, callback: Callable, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Registers a new approval request.
        """
        request_id = str(uuid.uuid4())[:8]
        self.pending_approvals[request_id] = {
            "action": action_type,
            "details": details,
            "callback": callback,
            "metadata": metadata or {},
            "requested_at": datetime.now().isoformat(),
            "status": "pending"
        }
        
        logger.info(f"  [HITL] Approval requested [{request_id}]: {action_type} - {details[:50]}...")
        return request_id

    def approve(self, request_id: str) -> bool:
        """
        Executes the callback for an approved request.
        """
        if request_id not in self.pending_approvals:
            return False
            
        req = self.pending_approvals[request_id]
        if req["status"] != "pending":
            return False
            
        logger.info(f"  [HITL] Action APPROVED: {request_id}")
        req["status"] = "approved"
        
        # Execute callback
        try:
            req["callback"](True, req["metadata"])
            return True
        except Exception as e:
            logger.error(f"  [HITL] Callback failed: {e}")
            return False
        finally:
            del self.pending_approvals[request_id]

    def reject(self, request_id: str) -> bool:
        """
        Rejects a request and notifies the requester.
        """
        if request_id not in self.pending_approvals:
            return False
            
        req = self.pending_approvals[request_id]
        logger.info(f"  [HITL] Action REJECTED: {request_id}")
        req["status"] = "rejected"
        
        try:
            req["callback"](False, req["metadata"])
            return True
        except Exception as e:
            logger.error(f"  [HITL] Callback failed: {e}")
            return False
        finally:
            del self.pending_approvals[request_id]

    def get_pending(self) -> List[Dict[str, Any]]:
        return [{"id": k, **v} for k, v in self.pending_approvals.items() if v["status"] == "pending"]

hitl_manager = HITLManager()
