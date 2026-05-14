from dataclasses import dataclass
from typing import Any, Dict, Optional

AUTHORIZATION_RESUME_TEXT = "continue"


@dataclass
class AuthorizationState:
    status: str = "idle"
    request_id: Optional[str] = None
    auth_url: Optional[str] = None
    reason_code: Optional[str] = None
    reason_message: Optional[str] = None


class AuthorizationCoordinator:
    def __init__(self) -> None:
        self.state = AuthorizationState()

    def reset(self) -> None:
        self.state = AuthorizationState()

    def extract_payload(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_inner = message.get("message", {})
        if isinstance(msg_inner, str):
            return None
        message_data = msg_inner.get("data", {})
        if not isinstance(message_data, dict):
            return None
        if message_data.get("type") != "x_api_authorize":
            return None
        return message_data

    def start(self, payload: Dict[str, Any]) -> Optional[str]:
        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            self.state = AuthorizationState(status="terminal_failure")
            return "x_api_authorize is missing request_id; cannot resume the current task."

        auth_url = str(payload.get("auth_url") or "").strip()
        if not auth_url:
            self.state = AuthorizationState(status="terminal_failure")
            return (
                "x_api_authorize is missing auth_url. SDK will not create a fallback "
                "authorization URL because it would lose the agent's same-round resume semantics."
            )

        self.state = AuthorizationState(
            status="pending_authorization",
            request_id=request_id,
            auth_url=auth_url,
            reason_code=str(payload.get("reason_code") or "").strip() or None,
            reason_message=str(payload.get("reason_message") or "").strip() or None,
        )
        return None

    def build_noninteractive_error(self) -> str:
        auth_url = self.state.auth_url or ""
        detail = (
            "X authorization is required. run_task() does not wait for interactive OAuth "
            "recovery; pre-authorize the X credential or switch to run_interactive_session()."
        )
        if auth_url:
            detail += f" Authorization URL: {auth_url}"
        return f"authorization_required: {detail}"

    @staticmethod
    def build_resume_prompt(browser_available: bool) -> str:
        if browser_available:
            return (
                "After completing authorization in the browser, return here and press Enter "
                "to continue this task."
            )
        return (
            "Open this URL in a browser on your local machine, finish authorization there, "
            "then return to this terminal and press Enter to continue this task."
        )

    @staticmethod
    def build_resume_text(user_input: str) -> str:
        return user_input or AUTHORIZATION_RESUME_TEXT
