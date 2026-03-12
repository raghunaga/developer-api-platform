"""Tests for Neo4j graph database integration."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from app.db.graph import (
    GraphDatabase, GraphQueryBuilder, PathFindingAlgorithm,
    GraphNode, GraphRelationship, GraphPath
)


class TestGraphDatabase:
    """Tests for GraphDatabase class."""

    def test_graph_database_initialization(self):
        """Test graph database initialization."""
        with patch('app.db.graph.NEO4J_AVAILABLE', True):
            db = GraphDatabase(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="password"
            )
            assert db.uri == "bolt://localhost:7687"
            assert db.username == "neo4j"
            assert db.password == "password"

    def test_graph_database_without_neo4j_driver(self):
        """Test graph database when Neo4j driver is not available."""
        with patch('app.db.graph.NEO4J_AVAILABLE', False):
            db = GraphDatabase()
            assert db.driver is None
            assert db.session is None

    def test_is_connected_when_not_connected(self):
        """Test is_connected returns False when not connected."""
        db = GraphDatabase()
        assert db.is_connected() is False

    def test_disconnect_when_not_connected(self):
        """Test disconnect when not connected."""
        db = GraphDatabase()
        db.disconnect()  # Should not raise an error


class TestGraphQueryBuilder:
    """Tests for GraphQueryBuilder class."""

    def test_query_builder_initialization(self):
        """Test query builder initialization."""
        session = Mock()
        builder = GraphQueryBuilder(session)
        assert builder.session == session
        assert builder.query == ""
        assert builder.parameters == {}

    def test_query_builder_without_session(self):
        """Test query builder without session."""
        builder = GraphQueryBuilder(None)
        assert builder.session is None

    def test_create_node_without_session(self):
        """Test create_node without session."""
        builder = GraphQueryBuilder(None)
        builder.create_node("node1", "TestNode", {"name": "Test"})
        # Should not raise an error

    def test_create_node_with_session(self):
        """Test create_node with session."""
        session = Mock()
        builder = GraphQueryBuilder(session)
        builder.create_node("node1", "TestNode", {"name": "Test"})
        session.run.assert_called_once()

    def test_create_relationship_without_session(self):
        """Test create_relationship without session."""
        builder = GraphQueryBuilder(None)
        builder.create_relationship("node1", "node2", "TEST_REL")
        # Should not raise an error

    def test_create_relationship_with_session(self):
        """Test create_relationship with session."""
        session = Mock()
        builder = GraphQueryBuilder(session)
        builder.create_relationship("node1", "node2", "TEST_REL")
        session.run.assert_called_once()

    def test_query_children_without_session(self):
        """Test query_children without session."""
        builder = GraphQueryBuilder(None)
        result = builder.query_children("node1")
        assert result == []

    def test_query_children_with_session(self):
        """Test query_children with session."""
        session = Mock()
        mock_node = Mock()
        mock_node.__getitem__ = Mock(side_effect=lambda x: "test_value" if x == "id" else None)
        mock_node.labels = ["TestNode"]

        mock_result = Mock()
        mock_result.__iter__ = Mock(return_value=iter([Mock(get=Mock(return_value=mock_node))]))

        session.run.return_value = mock_result

        builder = GraphQueryBuilder(session)
        result = builder.query_children("node1")
        assert isinstance(result, list)

    def test_query_parent_without_session(self):
        """Test query_parent without session."""
        builder = GraphQueryBuilder(None)
        result = builder.query_parent("node1")
        assert result is None

    def test_query_path_without_session(self):
        """Test query_path without session."""
        builder = GraphQueryBuilder(None)
        result = builder.query_path("node1", "node2")
        assert result is None

    def test_query_hierarchy_without_session(self):
        """Test query_hierarchy without session."""
        builder = GraphQueryBuilder(None)
        result = builder.query_hierarchy("node1")
        assert result == {}


class TestPathFindingAlgorithm:
    """Tests for PathFindingAlgorithm class."""

    def test_path_finding_initialization(self):
        """Test path finding algorithm initialization."""
        session = Mock()
        algo = PathFindingAlgorithm(session)
        assert algo.session == session
        assert isinstance(algo.query_builder, GraphQueryBuilder)

    def test_find_shortest_path_without_session(self):
        """Test find_shortest_path without session."""
        algo = PathFindingAlgorithm(None)
        result = algo.find_shortest_path("node1", "node2")
        assert result is None

    def test_find_all_paths_without_session(self):
        """Test find_all_paths without session."""
        algo = PathFindingAlgorithm(None)
        result = algo.find_all_paths("node1", "node2")
        assert result == []

    def test_find_common_ancestor_without_session(self):
        """Test find_common_ancestor without session."""
        algo = PathFindingAlgorithm(None)
        result = algo.find_common_ancestor("node1", "node2")
        assert result is None

    def test_find_descendants_without_session(self):
        """Test find_descendants without session."""
        algo = PathFindingAlgorithm(None)
        result = algo.find_descendants("node1")
        assert result == []

    def test_find_ancestors_without_session(self):
        """Test find_ancestors without session."""
        algo = PathFindingAlgorithm(None)
        result = algo.find_ancestors("node1")
        assert result == []


class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_graph_node_creation(self):
        """Test GraphNode creation."""
        node = GraphNode(
            node_id="node1",
            node_type="TestNode",
            properties={"name": "Test"}
        )
        assert node.node_id == "node1"
        assert node.node_type == "TestNode"
        assert node.properties == {"name": "Test"}


class TestGraphRelationship:
    """Tests for GraphRelationship dataclass."""

    def test_graph_relationship_creation(self):
        """Test GraphRelationship creation."""
        rel = GraphRelationship(
            source_id="node1",
            target_id="node2",
            relationship_type="TEST_REL",
            properties={"weight": 1}
        )
        assert rel.source_id == "node1"
        assert rel.target_id == "node2"
        assert rel.relationship_type == "TEST_REL"
        assert rel.properties == {"weight": 1}


class TestGraphPath:
    """Tests for GraphPath dataclass."""

    def test_graph_path_creation(self):
        """Test GraphPath creation."""
        nodes = [
            GraphNode("node1", "TestNode", {}),
            GraphNode("node2", "TestNode", {})
        ]
        relationships = [
            GraphRelationship("node1", "node2", "TEST_REL", {})
        ]
        path = GraphPath(nodes=nodes, relationships=relationships, length=2)
        assert len(path.nodes) == 2
        assert len(path.relationships) == 1
        assert path.length == 2


class TestGraphIntegration:
    """Integration tests for graph database."""

    def test_graph_node_properties(self):
        """Test that GraphNode stores properties correctly."""
        properties = {
            "id": "test-id",
            "name": "Test Node",
            "status": "active",
            "created_at": "2024-01-01T00:00:00"
        }
        node = GraphNode("test-id", "TestNode", properties)
        assert node.properties["name"] == "Test Node"
        assert node.properties["status"] == "active"

    def test_graph_path_with_multiple_nodes(self):
        """Test GraphPath with multiple nodes."""
        nodes = [
            GraphNode("node1", "Tenant", {"name": "Tenant1"}),
            GraphNode("node2", "Customer", {"name": "Customer1"}),
            GraphNode("node3", "Site", {"name": "Site1"}),
        ]
        relationships = [
            GraphRelationship("node1", "node2", "HAS_CUSTOMER", {}),
            GraphRelationship("node2", "node3", "HAS_SITE", {}),
        ]
        path = GraphPath(nodes=nodes, relationships=relationships, length=3)
        assert path.length == 3
        assert path.nodes[0].node_type == "Tenant"
        assert path.nodes[1].node_type == "Customer"
        assert path.nodes[2].node_type == "Site"
        assert path.relationships[0].relationship_type == "HAS_CUSTOMER"
        assert path.relationships[1].relationship_type == "HAS_SITE"
