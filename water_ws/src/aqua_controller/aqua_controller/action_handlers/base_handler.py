"""Base handler interface for action handlers."""

from abc import ABC, abstractmethod
from typing import Any
from rclpy.node import Node


class BaseHandler(ABC):
    """Abstract base class for action handlers.
    
    Subclasses must implement execute() method.
    """

    def __init__(self, node: Node):
        self._node = node

    @property
    def logger(self):
        return self._node.get_logger()

    @abstractmethod
    def execute(self, goal_handle: Any) -> Any:
        """Execute the action.
        
        Args:
            goal_handle: The action goal handle
            
        Returns:
            Action result
        """
        pass

    def publish_feedback(self, goal_handle: Any, feedback: Any) -> None:
        """Publish feedback to client."""
        goal_handle.publish_feedback(feedback)
