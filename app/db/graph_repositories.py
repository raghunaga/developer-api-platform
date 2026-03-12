"""Graph-based repositories for hierarchy queries."""

import logging
from typing import List, Optional, Dict, Any

from app.db.graph import GraphQueryBuilder, PathFindingAlgorithm, GraphNode, GraphPath

logger = logging.getLogger(__name__)


class GraphHierarchyRepository:
    """Repository for graph-based hierarchy queries."""

    def __init__(self, query_builder: GraphQueryBuilder, path_finder: PathFindingAlgorithm):
        """Initialize graph hierarchy repository."""
        self.query_builder = query_builder
        self.path_finder = path_finder

    def get_customer_hierarchy(self, customer_id: str) -> Dict[str, Any]:
        """Get the complete hierarchy for a customer."""
        try:
            hierarchy = self.query_builder.query_hierarchy(customer_id, max_depth=10)
            return hierarchy
        except Exception as e:
            logger.error(f"Failed to get customer hierarchy: {e}")
            return {}

    def get_site_hierarchy(self, site_id: str) -> Dict[str, Any]:
        """Get the complete hierarchy for a site."""
        try:
            hierarchy = self.query_builder.query_hierarchy(site_id, max_depth=10)
            return hierarchy
        except Exception as e:
            logger.error(f"Failed to get site hierarchy: {e}")
            return {}

    def get_device_hierarchy(self, device_id: str) -> Dict[str, Any]:
        """Get the complete hierarchy for a device."""
        try:
            hierarchy = self.query_builder.query_hierarchy(device_id, max_depth=10)
            return hierarchy
        except Exception as e:
            logger.error(f"Failed to get device hierarchy: {e}")
            return {}

    def get_children(self, node_id: str, node_type: str = None) -> List[GraphNode]:
        """Get all children of a node."""
        try:
            children = self.query_builder.query_children(node_id)
            return children
        except Exception as e:
            logger.error(f"Failed to get children: {e}")
            return []

    def get_parent(self, node_id: str) -> Optional[GraphNode]:
        """Get the parent of a node."""
        try:
            parent = self.query_builder.query_parent(node_id)
            return parent
        except Exception as e:
            logger.error(f"Failed to get parent: {e}")
            return None

    def get_path_to_root(self, node_id: str) -> Optional[GraphPath]:
        """Get the path from a node to the root (tenant)."""
        try:
            # This is a simplified version - in practice, you'd need to know the root ID
            # For now, we'll find ancestors instead
            ancestors = self.path_finder.find_ancestors(node_id)
            if ancestors:
                # Return the path to the topmost ancestor
                root = ancestors[-1]
                path = self.path_finder.find_shortest_path(node_id, root.node_id)
                return path
            return None
        except Exception as e:
            logger.error(f"Failed to get path to root: {e}")
            return None

    def get_path_between_nodes(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        """Get the shortest path between two nodes."""
        try:
            path = self.path_finder.find_shortest_path(source_id, target_id)
            return path
        except Exception as e:
            logger.error(f"Failed to get path between nodes: {e}")
            return None

    def get_all_descendants(self, node_id: str, max_depth: int = 10) -> List[GraphNode]:
        """Get all descendants of a node."""
        try:
            descendants = self.path_finder.find_descendants(node_id, max_depth)
            return descendants
        except Exception as e:
            logger.error(f"Failed to get descendants: {e}")
            return []

    def get_all_ancestors(self, node_id: str, max_depth: int = 10) -> List[GraphNode]:
        """Get all ancestors of a node."""
        try:
            ancestors = self.path_finder.find_ancestors(node_id, max_depth)
            return ancestors
        except Exception as e:
            logger.error(f"Failed to get ancestors: {e}")
            return []

    def get_common_ancestor(self, node_id_1: str, node_id_2: str) -> Optional[GraphNode]:
        """Get the common ancestor of two nodes."""
        try:
            ancestor = self.path_finder.find_common_ancestor(node_id_1, node_id_2)
            return ancestor
        except Exception as e:
            logger.error(f"Failed to get common ancestor: {e}")
            return None

    def get_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 10
    ) -> List[GraphPath]:
        """Get all paths between two nodes."""
        try:
            paths = self.path_finder.find_all_paths(source_id, target_id, max_length)
            return paths
        except Exception as e:
            logger.error(f"Failed to get all paths: {e}")
            return []


class GraphQueryRepository:
    """Repository for executing custom graph queries."""

    def __init__(self, query_builder: GraphQueryBuilder):
        """Initialize graph query repository."""
        self.query_builder = query_builder

    def execute_cypher_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute a custom Cypher query."""
        if not self.query_builder.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            parameters = parameters or {}
            result = self.query_builder.session.run(query, parameters)
            records = []
            for record in result:
                records.append(dict(record))
            return records
        except Exception as e:
            logger.error(f"Failed to execute Cypher query: {e}")
            return []

    def get_nodes_by_type(self, node_type: str) -> List[GraphNode]:
        """Get all nodes of a specific type."""
        if not self.query_builder.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            query = f"MATCH (n:{node_type}) RETURN n"
            result = self.query_builder.session.run(query)
            nodes = []
            for record in result:
                node = record["n"]
                nodes.append(GraphNode(
                    node_id=node["id"],
                    node_type=node_type,
                    properties=dict(node)
                ))
            return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes by type: {e}")
            return []

    def get_nodes_by_property(
        self,
        node_type: str,
        property_name: str,
        property_value: Any
    ) -> List[GraphNode]:
        """Get nodes by a specific property value."""
        if not self.query_builder.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            query = f"MATCH (n:{node_type} {{{property_name}: $value}}) RETURN n"
            result = self.query_builder.session.run(query, {"value": property_value})
            nodes = []
            for record in result:
                node = record["n"]
                nodes.append(GraphNode(
                    node_id=node["id"],
                    node_type=node_type,
                    properties=dict(node)
                ))
            return nodes
        except Exception as e:
            logger.error(f"Failed to get nodes by property: {e}")
            return []

    def count_nodes_by_type(self, node_type: str) -> int:
        """Count the number of nodes of a specific type."""
        if not self.query_builder.session:
            logger.warning("No session available. Skipping query.")
            return 0

        try:
            query = f"MATCH (n:{node_type}) RETURN count(n) as count"
            result = self.query_builder.session.run(query)
            record = result.single()
            if record:
                return record["count"]
            return 0
        except Exception as e:
            logger.error(f"Failed to count nodes: {e}")
            return 0

    def get_graph_statistics(self) -> Dict[str, Any]:
        """Get statistics about the graph."""
        if not self.query_builder.session:
            logger.warning("No session available. Skipping query.")
            return {}

        try:
            stats = {}

            # Count nodes by type
            node_types = ["Tenant", "Customer", "Site", "Gateway", "Device", "User", "DataStream"]
            for node_type in node_types:
                stats[f"{node_type}_count"] = self.count_nodes_by_type(node_type)

            # Count relationships
            query = "MATCH ()-[r]->() RETURN count(r) as count"
            result = self.query_builder.session.run(query)
            record = result.single()
            if record:
                stats["relationship_count"] = record["count"]

            return stats
        except Exception as e:
            logger.error(f"Failed to get graph statistics: {e}")
            return {}
