from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAgentTool(ABC):
    """
    Standard interface for all tools callable by the HRMS Agentic Engine.
    Provides standard name, description, schema validation, and execution wrapper.
    """
    name: str = ""
    description: str = ""
    parameters_schema: Dict[str, Any] = {}
    requires_human_approval: bool = False

    @abstractmethod
    def run(self, **kwargs) -> Dict[str, Any]:
        """Core execution logic implemented by the tool subclass."""
        raise NotImplementedError

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Public execution wrapper ensuring consistent output format and exception encapsulation.
        """
        try:
            result = self.run(**kwargs)
            if not isinstance(result, dict):
                result = {"result": result}
            return {
                "success": True,
                "tool": self.name,
                "data": result,
                "error": None,
            }
        except Exception as exc:
            return {
                "success": False,
                "tool": self.name,
                "data": {},
                "error": str(exc),
            }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters_schema": self.parameters_schema,
            "requires_human_approval": self.requires_human_approval,
        }
