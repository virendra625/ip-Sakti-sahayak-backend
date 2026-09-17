"""Knowledge Graph interface foundation for future Neo4j / NetworkX integration (Section 21).

Models entities: Product, Ingredient, Traditional Knowledge, Regulation, Law, IPR type,
Jurisdiction, Authority, Document, and their semantic relationships.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Generic Knowledge Graph node."""
    id: str
    label: str  # Product, Ingredient, Law, Regulation, Jurisdiction, Authority
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphRelationship(BaseModel):
    """Generic semantic relationship connecting two nodes."""
    source_id: str
    target_id: str
    relationship_type: str  # CONTAINS, CLASSIFIED_AS, ASSOCIATED_WITH, REGULATED_BY, GOVERNED_BY, BELONGS_TO
    properties: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeGraphInterface:
    """Abstract interface to be implemented by a Neo4j driver or in-memory NetworkX graph."""

    def add_node(self, node: GraphNode) -> None:
        """Inserts an entity node."""
        pass

    def add_relationship(self, rel: GraphRelationship) -> None:
        """Links two nodes via a typed edge."""
        pass

    def get_related_regulations(self, product_category: str) -> List[Dict[str, Any]]:
        """Queries regulations governing a specific Ayurvedic product category."""
        return []

    def get_ipr_laws_for_jurisdiction(self, jurisdiction: str) -> List[Dict[str, Any]]:
        """Queries statutory laws applicable to an IPR type in a given jurisdiction."""
        return []
