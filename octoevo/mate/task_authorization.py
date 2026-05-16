import json
from dataclasses import dataclass, field
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


@dataclass
class AccountSelectionState:
    request_id: Optional[str] = None
    accounts: list[dict[str, Any]] = field(default_factory=list)
    reason: Optional[str] = None


class AccountSelectionCoordinator:
    def __init__(self) -> None:
        self.state = AccountSelectionState()

    def reset(self) -> None:
        self.state = AccountSelectionState()

    def extract_payload(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_inner = message.get("message", {})
        if isinstance(msg_inner, str):
            return None
        message_data = msg_inner.get("data", {})
        if not isinstance(message_data, dict):
            return None
        if message_data.get("type") != "x_api_account_select":
            return None
        return message_data

    def start(self, payload: Dict[str, Any]) -> Optional[str]:
        request_id = str(payload.get("request_id") or "").strip()
        if not request_id:
            self.reset()
            return "x_api_account_select is missing request_id; cannot resume the current task."

        accounts = payload.get("accounts")
        if not isinstance(accounts, list) or not accounts:
            self.reset()
            return "x_api_account_select is missing accounts; cannot choose an X account."

        normalized = [item for item in accounts if isinstance(item, dict)]
        if not normalized:
            self.reset()
            return "x_api_account_select accounts payload is invalid."

        self.state = AccountSelectionState(
            request_id=request_id,
            accounts=normalized,
            reason=str(payload.get("reason") or "").strip() or None,
        )
        return None

    def build_noninteractive_error(self) -> str:
        return (
            "account_selection_required: Multiple X accounts are connected. "
            "run_task() cannot choose an account interactively; switch to run_interactive_session()."
        )

    @staticmethod
    def build_selection_response_text(selected: Dict[str, Any]) -> str:
        connector_id = str(selected.get("connector_id") or "").strip()
        if not connector_id:
            raise ValueError("x_api_account_select option is missing connector_id")
        payload = {"connector_id": connector_id}
        external_user_id = str(selected.get("external_user_id") or "").strip()
        if external_user_id:
            payload["external_user_id"] = external_user_id
        return json.dumps(payload, ensure_ascii=False)
