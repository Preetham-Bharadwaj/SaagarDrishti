"""Multi-agent orchestrator for coordinating domain-specific marine agents."""

import logging
from typing import Any, Dict, List
from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Coordinates lifecycle and execution of registered agents."""

    def __init__(self) -> None:
        self._registry: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a new specialized agent into the orchestrator.

        Args:
            agent: Instance of BaseAgent.
        """
        if agent.name in self._registry:
            logger.warning("Overwriting existing agent with name: %s", agent.name)
        self._registry[agent.name] = agent

    def get_registered_agents(self) -> List[str]:
        """Return names of all currently registered agents."""
        return list(self._registry.keys())

    async def dispatch(self, agent_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch a task to a registered agent.

        Args:
            agent_name: Identifier of the target agent.
            context: Execution context payload.

        Returns:
            Dict[str, Any]: Execution result from the agent.

        Raises:
            KeyError: If agent_name is not registered.
        """
        if agent_name not in self._registry:
            raise KeyError(f"Agent '{agent_name}' is not registered in orchestrator.")
        return await self._registry[agent_name].run(context)
