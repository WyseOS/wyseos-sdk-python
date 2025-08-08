"""
Plan models for the Wyse Mate Python SDK.

This module defines a unified plan data structure that supports both
- Wyse Mate plan (single-level list of steps)
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


class PlanStep(BaseModel):
    """A single plan step that can optionally contain sub-steps.

    It covers both:
    - Wyse Mate Plan: leaf steps with `agents`, `title`, `description`, no `steps`.
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

        # Show agents if present
        if self.agents:
            lines.append(f"{indent}  agents: {', '.join(self.agents)}")

        # Recurse into sub-steps
        for child in self.steps:
            lines.extend(child.render_lines(indent_level + 1))

        return lines


class Plan(BaseModel):
    """Unified plan object.

    Attributes:
        items: The root steps of the plan. For Wyse Mate, these are leaf steps.
               For Deep Research, these can be group steps containing `steps`.
    """

    items: List[PlanStep] = Field(default_factory=list)

    @property
    def is_nested(self) -> bool:
        """True if any root item contains sub-steps."""
        return any(len(step.steps) > 0 for step in self.items)

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
        """Build a Plan from a message payload."""
        items_raw = cls._coerce_to_items(message)
        items = [PlanStep.model_validate(item) for item in items_raw]

        return cls(items=items)

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
