"""Neo4j graph database integration for hierarchy relationships."""

import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

try:
    from neo4j import GraphDatabase, Session as Neo4jSession
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    Neo4jSession = None

logger = logging.getLogger(__name__)


@dataclass
class GraphNode:
    """Represents a node in the graph."""
    node_id: str
    node_type: str
    properties: Dict[str, Any]


@dataclass
class GraphRelationship:
    """Represents a relationship between nodes."""
    source_id: str
    target_id: str
    relationship_type: str
    properties: Dict[str, Any]


@dataclass
class GraphPath:
    """Represents a path through the graph."""
    nodes: List[GraphNode]
    relationships: List[GraphRelationship]
    length: int


class GraphDatabase:
    """Neo4j graph database connection manager."""

    def __init__(self, uri: str = None, username: str = None, password: str = None):
        """Initialize graph database connection."""
        if not NEO4J_AVAILABLE:
            logger.warning("Neo4j driver not available. Graph operations will be disabled.")
            self.driver = None
            self.session = None
            return

        self.uri = uri or "bolt://localhost:7687"
        self.username = username or "neo4j"
        self.password = password or "password"
        self.driver = None
        self.session = None

    def connect(self) -> None:
        """Connect to Neo4j database."""
        if not NEO4J_AVAILABLE:
            logger.warning("Cannot connect to Neo4j: driver not available")
            return

        try:
            logger.info(f"Connecting to Neo4j at {self.uri}")
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password),
                encrypted=False
            )
            self.session = self.driver.session()
            logger.info("Connected to Neo4j successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None
            self.session = None

    def disconnect(self) -> None:
        """Disconnect from Neo4j database."""
        if self.session:
            self.session.close()
        if self.driver:
            self.driver.close()
        logger.info("Disconnected from Neo4j")

    def is_connected(self) -> bool:
        """Check if connected to Neo4j."""
        return self.driver is not None and self.session is not None

    def create_schema(self) -> None:
        """Create graph schema with constraints and indexes."""
        if not self.is_connected():
            logger.warning("Not connected to Neo4j. Skipping schema creation.")
            return

        try:
            logger.info("Creating Neo4j graph schema")

            # Create constraints for unique identifiers
            constraints = [
                "CREATE CONSTRAINT tenant_id IF NOT EXISTS FOR (t:Tenant) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT site_id IF NOT EXISTS FOR (s:Site) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT gateway_id IF NOT EXISTS FOR (g:Gateway) REQUIRE g.id IS UNIQUE",
                "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
                "CREATE CONSTRAINT user_id IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE",
                "CREATE CONSTRAINT datastream_id IF NOT EXISTS FOR (ds:DataStream) REQUIRE ds.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    self.session.run(constraint)
                    logger.debug(f"Created constraint: {constraint}")
                except Exception as e:
                    logger.debug(f"Constraint already exists or error: {e}")

            # Create indexes for frequently accessed properties
            indexes = [
                "CREATE INDEX tenant_identifier IF NOT EXISTS FOR (t:Tenant) ON (t.identifier)",
                "CREATE INDEX customer_identifier IF NOT EXISTS FOR (c:Customer) ON (c.identifier)",
                "CREATE INDEX site_identifier IF NOT EXISTS FOR (s:Site) ON (s.identifier)",
                "CREATE INDEX gateway_identifier IF NOT EXISTS FOR (g:Gateway) ON (g.identifier)",
                "CREATE INDEX device_identifier IF NOT EXISTS FOR (d:Device) ON (d.identifier)",
                "CREATE INDEX user_identifier IF NOT EXISTS FOR (u:User) ON (u.identifier)",
                "CREATE INDEX datastream_identifier IF NOT EXISTS FOR (ds:DataStream) ON (ds.identifier)",
                "CREATE INDEX device_status IF NOT EXISTS FOR (d:Device) ON (d.status)",
                "CREATE INDEX gateway_status IF NOT EXISTS FOR (g:Gateway) ON (g.status)",
            ]

            for index in indexes:
                try:
                    self.session.run(index)
                    logger.debug(f"Created index: {index}")
                except Exception as e:
                    logger.debug(f"Index already exists or error: {e}")

            logger.info("Graph schema created successfully")
        except Exception as e:
            logger.error(f"Failed to create graph schema: {e}")

    def clear_graph(self) -> None:
        """Clear all nodes and relationships from the graph."""
        if not self.is_connected():
            logger.warning("Not connected to Neo4j. Skipping graph clear.")
            return

        try:
            logger.warning("Clearing all nodes and relationships from Neo4j")
            self.session.run("MATCH (n) DETACH DELETE n")
            logger.info("Graph cleared successfully")
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")


class GraphQueryBuilder:
    """Builder for constructing Neo4j graph queries."""

    def __init__(self, session: Optional[Neo4jSession] = None):
        """Initialize query builder."""
        self.session = session
        self.query = ""
        self.parameters = {}

    def create_node(self, node_id: str, node_type: str, properties: Dict[str, Any]) -> None:
        """Create a node in the graph."""
        if not self.session:
            logger.warning("No session available. Skipping node creation.")
            return

        try:
            query = f"""
            CREATE (n:{node_type} {{id: $id}})
            SET n += $properties
            RETURN n
            """
            params = {"id": node_id, "properties": properties}
            self.session.run(query, params)
            logger.debug(f"Created node: {node_type}({node_id})")
        except Exception as e:
            logger.error(f"Failed to create node: {e}")

    def create_relationship(
        self,
        source_id: str,
        target_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None
    ) -> None:
        """Create a relationship between two nodes."""
        if not self.session:
            logger.warning("No session available. Skipping relationship creation.")
            return

        try:
            properties = properties or {}
            query = f"""
            MATCH (source {{id: $source_id}})
            MATCH (target {{id: $target_id}})
            CREATE (source)-[r:{relationship_type}]->(target)
            SET r += $properties
            RETURN r
            """
            params = {
                "source_id": source_id,
                "target_id": target_id,
                "properties": properties
            }
            self.session.run(query, params)
            logger.debug(f"Created relationship: {source_id} -[{relationship_type}]-> {target_id}")
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")

    def query_children(self, node_id: str, relationship_type: str = None) -> List[GraphNode]:
        """Query all children of a node."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            rel_filter = f":{relationship_type}" if relationship_type else ""
            query = f"""
            MATCH (parent {{id: $node_id}})-[{rel_filter}]->(child)
            RETURN child
            """
            result = self.session.run(query, {"node_id": node_id})
            nodes = []
            for record in result:
                child = record["child"]
                nodes.append(GraphNode(
                    node_id=child["id"],
                    node_type=list(child.labels)[0] if child.labels else "Unknown",
                    properties=dict(child)
                ))
            return nodes
        except Exception as e:
            logger.error(f"Failed to query children: {e}")
            return []

    def query_parent(self, node_id: str, relationship_type: str = None) -> Optional[GraphNode]:
        """Query the parent of a node."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return None

        try:
            rel_filter = f":{relationship_type}" if relationship_type else ""
            query = f"""
            MATCH (child {{id: $node_id}})<-[{rel_filter}]-(parent)
            RETURN parent
            LIMIT 1
            """
            result = self.session.run(query, {"node_id": node_id})
            record = result.single()
            if record:
                parent = record["parent"]
                return GraphNode(
                    node_id=parent["id"],
                    node_type=list(parent.labels)[0] if parent.labels else "Unknown",
                    properties=dict(parent)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to query parent: {e}")
            return None

    def query_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        """Query the shortest path between two nodes."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return None

        try:
            query = """
            MATCH path = shortestPath((source {id: $source_id})-[*]-(target {id: $target_id}))
            RETURN path
            """
            result = self.session.run(query, {"source_id": source_id, "target_id": target_id})
            record = result.single()
            if record:
                path = record["path"]
                nodes = []
                relationships = []

                # Extract nodes from path
                for node in path.nodes:
                    nodes.append(GraphNode(
                        node_id=node["id"],
                        node_type=list(node.labels)[0] if node.labels else "Unknown",
                        properties=dict(node)
                    ))

                # Extract relationships from path
                for rel in path.relationships:
                    relationships.append(GraphRelationship(
                        source_id=rel.start_node["id"],
                        target_id=rel.end_node["id"],
                        relationship_type=rel.type,
                        properties=dict(rel)
                    ))

                return GraphPath(
                    nodes=nodes,
                    relationships=relationships,
                    length=len(path)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to query path: {e}")
            return None

    def query_hierarchy(self, root_id: str, max_depth: int = 10) -> Dict[str, Any]:
        """Query the complete hierarchy starting from a root node."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return {}

        try:
            query = """
            MATCH (root {id: $root_id})
            CALL apoc.path.subgraphAll(root, {maxLevel: $max_depth})
            YIELD nodes, relationships
            RETURN nodes, relationships
            """
            result = self.session.run(query, {"root_id": root_id, "max_depth": max_depth})
            record = result.single()
            if record:
                nodes = []
                relationships = []

                for node in record["nodes"]:
                    nodes.append(GraphNode(
                        node_id=node["id"],
                        node_type=list(node.labels)[0] if node.labels else "Unknown",
                        properties=dict(node)
                    ))

                for rel in record["relationships"]:
                    relationships.append(GraphRelationship(
                        source_id=rel.start_node["id"],
                        target_id=rel.end_node["id"],
                        relationship_type=rel.type,
                        properties=dict(rel)
                    ))

                return {
                    "nodes": nodes,
                    "relationships": relationships,
                    "node_count": len(nodes),
                    "relationship_count": len(relationships)
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to query hierarchy: {e}")
            return {}


class PathFindingAlgorithm:
    """Path-finding algorithms for hierarchy navigation."""

    def __init__(self, session: Optional[Neo4jSession] = None):
        """Initialize path-finding algorithm."""
        self.session = session
        self.query_builder = GraphQueryBuilder(session)

    def find_shortest_path(self, source_id: str, target_id: str) -> Optional[GraphPath]:
        """Find the shortest path between two nodes."""
        return self.query_builder.query_path(source_id, target_id)

    def find_all_paths(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 10
    ) -> List[GraphPath]:
        """Find all paths between two nodes up to max_length."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            query = """
            MATCH path = (source {id: $source_id})-[*1..$max_length]-(target {id: $target_id})
            RETURN path
            """
            result = self.session.run(query, {
                "source_id": source_id,
                "target_id": target_id,
                "max_length": max_length
            })

            paths = []
            for record in result:
                path = record["path"]
                nodes = []
                relationships = []

                for node in path.nodes:
                    nodes.append(GraphNode(
                        node_id=node["id"],
                        node_type=list(node.labels)[0] if node.labels else "Unknown",
                        properties=dict(node)
                    ))

                for rel in path.relationships:
                    relationships.append(GraphRelationship(
                        source_id=rel.start_node["id"],
                        target_id=rel.end_node["id"],
                        relationship_type=rel.type,
                        properties=dict(rel)
                    ))

                paths.append(GraphPath(
                    nodes=nodes,
                    relationships=relationships,
                    length=len(path)
                ))

            return paths
        except Exception as e:
            logger.error(f"Failed to find all paths: {e}")
            return []

    def find_common_ancestor(self, node_id_1: str, node_id_2: str) -> Optional[GraphNode]:
        """Find the common ancestor of two nodes."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return None

        try:
            query = """
            MATCH (node1 {id: $node_id_1})<-[*]-(ancestor)-[*]->(node2 {id: $node_id_2})
            RETURN ancestor
            LIMIT 1
            """
            result = self.session.run(query, {
                "node_id_1": node_id_1,
                "node_id_2": node_id_2
            })
            record = result.single()
            if record:
                ancestor = record["ancestor"]
                return GraphNode(
                    node_id=ancestor["id"],
                    node_type=list(ancestor.labels)[0] if ancestor.labels else "Unknown",
                    properties=dict(ancestor)
                )
            return None
        except Exception as e:
            logger.error(f"Failed to find common ancestor: {e}")
            return None

    def find_descendants(self, node_id: str, max_depth: int = 10) -> List[GraphNode]:
        """Find all descendants of a node."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            query = """
            MATCH (root {id: $node_id})-[*1..$max_depth]->(descendant)
            RETURN DISTINCT descendant
            """
            result = self.session.run(query, {
                "node_id": node_id,
                "max_depth": max_depth
            })

            descendants = []
            for record in result:
                descendant = record["descendant"]
                descendants.append(GraphNode(
                    node_id=descendant["id"],
                    node_type=list(descendant.labels)[0] if descendant.labels else "Unknown",
                    properties=dict(descendant)
                ))

            return descendants
        except Exception as e:
            logger.error(f"Failed to find descendants: {e}")
            return []

    def find_ancestors(self, node_id: str, max_depth: int = 10) -> List[GraphNode]:
        """Find all ancestors of a node."""
        if not self.session:
            logger.warning("No session available. Skipping query.")
            return []

        try:
            query = """
            MATCH (leaf {id: $node_id})<-[*1..$max_depth]-(ancestor)
            RETURN DISTINCT ancestor
            """
            result = self.session.run(query, {
                "node_id": node_id,
                "max_depth": max_depth
            })

            ancestors = []
            for record in result:
                ancestor = record["ancestor"]
                ancestors.append(GraphNode(
                    node_id=ancestor["id"],
                    node_type=list(ancestor.labels)[0] if ancestor.labels else "Unknown",
                    properties=dict(ancestor)
                ))

            return ancestors
        except Exception as e:
            logger.error(f"Failed to find ancestors: {e}")
            return []
