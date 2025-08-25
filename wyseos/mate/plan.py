"""
Plan models for the WyseOS Python SDK.

This module defines a unified plan data structure that supports both
- Wyse OS plan (single-level list of steps)
- Deep Research plan (two-level nested steps)
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

STATUS_EMOJI = {
    "not_started": "[ ]",
    "in_progress": "[~]",
    "done": "[√]",
    "skipped": "[-]",
    "error": "[!]",
}


class PlanStatus(str, Enum):
    """Status for a plan step."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    SKIPPED = "skipped"
    ERROR = "error"


class PlanOverallStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class PlanStep(BaseModel):
    """A single plan step that can optionally contain sub-steps.

    It covers both:
    - Wyse OS Plan: leaf steps with `agents`, `title`, `description`, no `steps`.
    - Deep Research Plan: group steps (with `steps`) and child leaf steps.
    """

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    status: PlanStatus = Field(default=PlanStatus.NOT_STARTED)
    agents: List[str] = Field(default_factory=list)
    steps: List["PlanStep"] = Field(default_factory=list)

    def is_leaf(self) -> bool:
        """Return True if the step has no sub-steps."""
        return len(self.steps) == 0

    def render_lines(self, indent_level: int = 0) -> List[str]:
        """Render this step and its sub-steps into a list of outline lines."""
        indent = "  " * indent_level
        status_key = getattr(self.status, "value", str(self.status))
        emoji = STATUS_EMOJI.get(status_key, "[ ]")
        title_or_desc = self.title or self.description or self.id

        lines: List[str] = [f"{indent}{emoji} {title_or_desc}"]

        # Show description if distinct from title
        if self.title and self.description and self.description != self.title:
            lines.append(f"{indent}  - {self.description}")

        # Recurse into sub-steps
        for child in self.steps:
            lines.extend(child.render_lines(indent_level + 1))

        return lines


class Plan(BaseModel):
    """Unified plan object.

    Attributes:
        items: The root steps of the plan. For Wyse OS, these are leaf steps.
               For Deep Research, these can be group steps containing `steps`.
    """

    items: List[PlanStep] = Field(default_factory=list)

    @property
    def is_nested(self) -> bool:
        """True if any root item contains sub-steps."""
        return any(len(step.steps) > 0 for step in self.items)

    def get_overall_status(self) -> PlanOverallStatus:
        """Return overall status of the plan.

        - NOT_STARTED: all top-level steps are not_started (or no items)
        - FINISHED: all leaf steps are in terminal states (done/skipped/error)
        - IN_PROGRESS: otherwise
        """
        if not self.items:
            return PlanOverallStatus.NOT_STARTED

        # Check top-level not started
        if all(step.status == PlanStatus.NOT_STARTED for step in self.items):
            return PlanOverallStatus.NOT_STARTED

        # Determine finished based on leaves (last-level tasks)
        leaves = self.leaves()
        if leaves:
            terminal = {PlanStatus.DONE, PlanStatus.SKIPPED, PlanStatus.ERROR}
            if all(step.status in terminal for step in leaves):
                return PlanOverallStatus.FINISHED

        return PlanOverallStatus.IN_PROGRESS

    def find(self, step_id: str) -> Optional[PlanStep]:
        """Find a step by id (depth-first)."""

        def _dfs(steps: List[PlanStep]) -> Optional[PlanStep]:
            for s in steps:
                if s.id == step_id:
                    return s
                found = _dfs(s.steps)
                if found:
                    return found
            return None

        return _dfs(self.items)

    def flatten(self) -> List[PlanStep]:
        """Return all steps in depth-first order (including group steps)."""
        result: List[PlanStep] = []

        def _walk(steps: List[PlanStep]) -> None:
            for s in steps:
                result.append(s)
                if s.steps:
                    _walk(s.steps)

        _walk(self.items)
        return result

    def leaves(self) -> List[PlanStep]:
        """Return only leaf steps (no sub-steps)."""
        return [s for s in self.flatten() if s.is_leaf()]

    def render_lines(self) -> List[str]:
        """Render the whole plan into a list of outline lines."""
        lines: List[str] = []
        for root in self.items:
            lines.extend(root.render_lines(0))
        return lines

    def render_text(self) -> str:
        """Render the plan as a human-readable multi-line string."""
        return "\n".join(self.render_lines())

    @staticmethod
    def _coerce_to_items(source: Any) -> List[Dict[str, Any]]:
        """Extract the list of item dicts from a variety of inputs.

        Accepts the following forms and returns a list of step-like dicts:
        - Direct list of steps
        - Dict with "data" key
        - Dict with "message" -> { "data": [...] }
        """
        if source is None:
            return []

        # If it's already a list of dicts/steps
        if isinstance(source, list):
            return source

        if isinstance(source, dict):
            # message.data
            if "message" in source and isinstance(source["message"], dict):
                msg = source["message"]
                if isinstance(msg.get("data"), list):
                    return msg["data"]

            # direct .data
            if isinstance(source.get("data"), list):
                return source["data"]

        return []

    @classmethod
    def from_message(cls, message: Any) -> "Plan":
        """Build a Plan from a message payload (initial plan only)."""
        items_raw = cls._coerce_to_items(message)
        items = [PlanStep.model_validate(item) for item in items_raw]
        return cls(items=items)

    @staticmethod
    def is_update_message(message: Any) -> bool:
        """Return True if the payload looks like a plan update (not a full plan)."""
        if not isinstance(message, dict):
            return False
        msg = message.get("message")
        if not isinstance(msg, dict):
            return False
        msg_type = msg.get("type")
        if isinstance(msg_type, str) and msg_type == "update_task_status":
            return True
        # If message.data is a dict (single task), treat as update
        data = msg.get("data") if isinstance(msg, dict) else None
        return isinstance(data, dict)

    def _ensure_step(self, step_like: Dict[str, Any]) -> PlanStep:
        """Ensure a step with given id exists; create or update and return it."""
        step_id = str(step_like.get("id")) if step_like.get("id") is not None else None
        if not step_id:
            # If no id, generate a simple deterministic id from title
            title = step_like.get("title") or step_like.get("description") or "unnamed"
            step_id = title
        existing = self.find(step_id)
        if existing:
            # Update simple fields
            if "title" in step_like and step_like["title"]:
                existing.title = step_like["title"]
            if "description" in step_like and step_like["description"]:
                existing.description = step_like["description"]
            if "agents" in step_like and isinstance(step_like["agents"], list):
                existing.agents = list(step_like["agents"])
            if "status" in step_like and step_like["status"]:
                try:
                    existing.status = PlanStatus(step_like["status"])  # may raise
                except Exception:
                    pass
            return existing
        # Create new leaf step when not found
        new_step_data: Dict[str, Any] = {
            "id": step_id,
            "title": step_like.get("title"),
            "description": step_like.get("description"),
            "agents": step_like.get("agents") or [],
        }
        if step_like.get("status"):
            try:
                new_step_data["status"] = PlanStatus(step_like["status"])  # type: ignore
            except Exception:
                pass
        new_step = PlanStep.model_validate(new_step_data)
        self.items.append(new_step)
        return new_step

    def apply_message(self, message: Any) -> bool:
        """Apply a plan-related message to this instance.

        - If it's an initial/full plan, replace items with provided steps.
        - If it's an update (single task dict), update or create the step by id.
        Returns True if any state was changed.
        """
        if not isinstance(message, dict):
            return False

        # Full plan
        items_raw = self._coerce_to_items(message)
        if items_raw:
            self.items = [PlanStep.model_validate(item) for item in items_raw]
            return True

        # Update message
        msg = message.get("message")
        if not isinstance(msg, dict):
            return False
        data = msg.get("data")
        if not isinstance(data, dict):
            return False

        before = self.render_text()
        self._ensure_step(data)
        after = self.render_text()
        return before != after

    def to_message_data(self) -> List[Dict[str, Any]]:
        """Serialize back to the `message.data` shape (list of dicts)."""
        return [item.model_dump(exclude_none=True) for item in self.items]


class AcceptPlan(BaseModel):
    """Acceptance payload for plan confirmation.
    It's like: {"accepted": true, "plan": [], "content": ""}
    """

    accepted: bool = True
    plan: List[PlanStep] = Field(default_factory=list)
    content: str = ""

    @classmethod
    def create(
        cls,
        accepted: bool = True,
        plan: Optional[List[PlanStep]] = None,
        content: str = "",
    ) -> "AcceptPlan":
        return cls(accepted=accepted, plan=plan or [], content=content)

    def to_message_json(self) -> str:
        """Serialize to the TEXT message `content` JSON string."""
        import json

        payload = {
            "accepted": bool(self.accepted),
            "plan": [step.model_dump(exclude_none=True) for step in self.plan],
            "content": self.content or "",
        }
        return json.dumps(payload)
