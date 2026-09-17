"""Agent orchestration interfaces for future multi-agent expansion (Section 22).

Defines interfaces for specialized decision agents:
- ClassificationAgent
- IPRAgent
- RegulatoryAgent
- TraditionalKnowledgeAgent
- JurisdictionAgent
- OrchestratorAgent
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class AgentState(BaseModel):
    """Shared state passed between specialized agents."""
    user_query: str
    jurisdiction: str = "India"
    language: str = "en"
    product_data: Optional[Dict[str, Any]] = None
    classification: Optional[Dict[str, Any]] = None
    retrieved_chunks: list = []
    ipr_guidance: Optional[str] = None
    regulatory_guidance: Optional[str] = None
    final_answer: Optional[str] = None


class BaseSpecializedAgent:
    """Base class for domain-specific decision agents."""

    def __init__(self, name: str):
        self.name = name

    async def execute(self, state: AgentState) -> AgentState:
        """Executes domain analysis and enriches shared agent state."""
        return state


class ClassificationAgent(BaseSpecializedAgent):
    """Classifies formulation into ASU, Phytopharmaceutical, or Ayurveda Aahar."""
    def __init__(self):
        super().__init__("ClassificationAgent")


class IPRAgent(BaseSpecializedAgent):
    """Evaluates patentability (Section 3(p)), trademarks, and geographical indications."""
    def __init__(self):
        super().__init__("IPRAgent")


class RegulatoryAgent(BaseSpecializedAgent):
    """Evaluates AYUSH licensing, Rule 158-B, clinical requirements, and labelling."""
    def __init__(self):
        super().__init__("RegulatoryAgent")


class TraditionalKnowledgeAgent(BaseSpecializedAgent):
    """Assesses TKDL references and classical text listings."""
    def __init__(self):
        super().__init__("TraditionalKnowledgeAgent")


class JurisdictionAgent(BaseSpecializedAgent):
    """Validates jurisdictional boundaries and guards against cross-country mixing."""
    def __init__(self):
        super().__init__("JurisdictionAgent")


class OrchestratorAgent:
    """Coordinates execution pipeline between specialized agents."""

    def __init__(self):
        self.agents = [
            JurisdictionAgent(),
            ClassificationAgent(),
            TraditionalKnowledgeAgent(),
            IPRAgent(),
            RegulatoryAgent(),
        ]

    async def run_workflow(self, initial_state: AgentState) -> AgentState:
        state = initial_state
        for agent in self.agents:
            state = await agent.execute(state)
        return state
