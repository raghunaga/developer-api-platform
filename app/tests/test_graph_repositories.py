"""Tests for graph-based repositories."""

import pytest
from unittest.mock import Mock, MagicMock

from app.db.graph_repositories import GraphHierarchyRepository, GraphQueryRepository
from app.db.graph import GraphQueryBuilder, PathFindingAlgorithm, GraphNode, GraphPath


class TestGraphHierarchyRepository:
    """Tests for GraphHierarchyRepository class."""

    def test_repository_initialization(self):
        """Test repository initialization."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)
        repo = GraphHierarchyRepository(query_builder, path_finder)
        assert repo.query_builder == query_builder
        assert repo.path_finder == path_finder

    def test_get_customer_hierarchy(self):
        """Test getting customer hierarchy."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.query_hierarchy.return_value = {
            "nodes": [],
            "relationships": [],
            "node_count": 0,
            "relationship_count": 0
        }
        path_finder = Mock(spec=PathFindingAlgorithm)

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_customer_hierarchy("customer-1")
        assert isinstance(result, dict)
        query_builder.query_hierarchy.assert_called_once_with("customer-1", max_depth=10)

    def test_get_site_hierarchy(self):
        """Test getting site hierarchy."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.query_hierarchy.return_value = {}
        path_finder = Mock(spec=PathFindingAlgorithm)

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_site_hierarchy("site-1")
        assert isinstance(result, dict)
        query_builder.query_hierarchy.assert_called_once_with("site-1", max_depth=10)

    def test_get_device_hierarchy(self):
        """Test getting device hierarchy."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.query_hierarchy.return_value = {}
        path_finder = Mock(spec=PathFindingAlgorithm)

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_device_hierarchy("device-1")
        assert isinstance(result, dict)
        query_builder.query_hierarchy.assert_called_once_with("device-1", max_depth=10)

    def test_get_children(self):
        """Test getting children of a node."""
        query_builder = Mock(spec=GraphQueryBuilder)
        child_node = GraphNode("child-1", "Site", {"name": "Child"})
        query_builder.query_children.return_value = [child_node]
        path_finder = Mock(spec=PathFindingAlgorithm)

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_children("parent-1")
        assert len(result) == 1
        assert result[0].node_id == "child-1"

    def test_get_parent(self):
        """Test getting parent of a node."""
        query_builder = Mock(spec=GraphQueryBuilder)
        parent_node = GraphNode("parent-1", "Customer", {"name": "Parent"})
        query_builder.query_parent.return_value = parent_node
        path_finder = Mock(spec=PathFindingAlgorithm)

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_parent("child-1")
        assert result.node_id == "parent-1"

    def test_get_path_to_root(self):
        """Test getting path to root."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        root_node = GraphNode("root-1", "Tenant", {"name": "Root"})
        path_finder.find_ancestors.return_value = [root_node]

        path = GraphPath(
            nodes=[
                GraphNode("node-1", "Device", {}),
                GraphNode("root-1", "Tenant", {})
            ],
            relationships=[],
            length=2
        )
        path_finder.find_shortest_path.return_value = path

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_path_to_root("node-1")
        assert result is not None
        assert result.length == 2

    def test_get_path_between_nodes(self):
        """Test getting path between two nodes."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        path = GraphPath(
            nodes=[
                GraphNode("node-1", "Device", {}),
                GraphNode("node-2", "Device", {})
            ],
            relationships=[],
            length=2
        )
        path_finder.find_shortest_path.return_value = path

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_path_between_nodes("node-1", "node-2")
        assert result is not None
        assert result.length == 2

    def test_get_all_descendants(self):
        """Test getting all descendants."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        descendants = [
            GraphNode("desc-1", "Site", {}),
            GraphNode("desc-2", "Gateway", {}),
            GraphNode("desc-3", "Device", {})
        ]
        path_finder.find_descendants.return_value = descendants

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_all_descendants("parent-1")
        assert len(result) == 3

    def test_get_all_ancestors(self):
        """Test getting all ancestors."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        ancestors = [
            GraphNode("anc-1", "Gateway", {}),
            GraphNode("anc-2", "Site", {}),
            GraphNode("anc-3", "Tenant", {})
        ]
        path_finder.find_ancestors.return_value = ancestors

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_all_ancestors("child-1")
        assert len(result) == 3

    def test_get_common_ancestor(self):
        """Test getting common ancestor."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        ancestor = GraphNode("ancestor-1", "Site", {"name": "Common"})
        path_finder.find_common_ancestor.return_value = ancestor

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_common_ancestor("node-1", "node-2")
        assert result.node_id == "ancestor-1"

    def test_get_all_paths(self):
        """Test getting all paths."""
        query_builder = Mock(spec=GraphQueryBuilder)
        path_finder = Mock(spec=PathFindingAlgorithm)

        paths = [
            GraphPath(
                nodes=[GraphNode("node-1", "Device", {}), GraphNode("node-2", "Device", {})],
                relationships=[],
                length=2
            )
        ]
        path_finder.find_all_paths.return_value = paths

        repo = GraphHierarchyRepository(query_builder, path_finder)
        result = repo.get_all_paths("node-1", "node-2")
        assert len(result) == 1


class TestGraphQueryRepository:
    """Tests for GraphQueryRepository class."""

    def test_repository_initialization(self):
        """Test repository initialization."""
        query_builder = Mock(spec=GraphQueryBuilder)
        repo = GraphQueryRepository(query_builder)
        assert repo.query_builder == query_builder

    def test_execute_cypher_query(self):
        """Test executing a Cypher query."""
        query_builder = Mock(spec=GraphQueryBuilder)
        session = Mock()
        query_builder.session = session

        mock_record = Mock()
        mock_record.__iter__ = Mock(return_value=iter([("key", "value")]))
        session.run.return_value = [mock_record]

        repo = GraphQueryRepository(query_builder)
        result = repo.execute_cypher_query("MATCH (n) RETURN n")
        assert isinstance(result, list)

    def test_execute_cypher_query_without_session(self):
        """Test executing a Cypher query without session."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.session = None

        repo = GraphQueryRepository(query_builder)
        result = repo.execute_cypher_query("MATCH (n) RETURN n")
        assert result == []

    def test_get_nodes_by_type(self):
        """Test getting nodes by type."""
        query_builder = Mock(spec=GraphQueryBuilder)
        session = Mock()
        query_builder.session = session

        mock_node = Mock()
        mock_node.__getitem__ = Mock(side_effect=lambda x: "test-id" if x == "id" else None)
        mock_node.labels = ["Device"]

        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=mock_node)
        session.run.return_value = [mock_record]

        repo = GraphQueryRepository(query_builder)
        result = repo.get_nodes_by_type("Device")
        assert isinstance(result, list)

    def test_get_nodes_by_type_without_session(self):
        """Test getting nodes by type without session."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.session = None

        repo = GraphQueryRepository(query_builder)
        result = repo.get_nodes_by_type("Device")
        assert result == []

    def test_get_nodes_by_property(self):
        """Test getting nodes by property."""
        query_builder = Mock(spec=GraphQueryBuilder)
        session = Mock()
        query_builder.session = session

        mock_node = Mock()
        mock_node.__getitem__ = Mock(side_effect=lambda x: "test-id" if x == "id" else None)
        mock_node.labels = ["Device"]

        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=mock_node)
        session.run.return_value = [mock_record]

        repo = GraphQueryRepository(query_builder)
        result = repo.get_nodes_by_property("Device", "status", "online")
        assert isinstance(result, list)

    def test_count_nodes_by_type(self):
        """Test counting nodes by type."""
        query_builder = Mock(spec=GraphQueryBuilder)
        session = Mock()
        query_builder.session = session

        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=5)
        session.run.return_value.single.return_value = mock_record

        repo = GraphQueryRepository(query_builder)
        result = repo.count_nodes_by_type("Device")
        assert result == 5

    def test_count_nodes_by_type_without_session(self):
        """Test counting nodes by type without session."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.session = None

        repo = GraphQueryRepository(query_builder)
        result = repo.count_nodes_by_type("Device")
        assert result == 0

    def test_get_graph_statistics(self):
        """Test getting graph statistics."""
        query_builder = Mock(spec=GraphQueryBuilder)
        session = Mock()
        query_builder.session = session

        mock_record = Mock()
        mock_record.__getitem__ = Mock(return_value=10)
        session.run.return_value.single.return_value = mock_record

        repo = GraphQueryRepository(query_builder)
        result = repo.get_graph_statistics()
        assert isinstance(result, dict)

    def test_get_graph_statistics_without_session(self):
        """Test getting graph statistics without session."""
        query_builder = Mock(spec=GraphQueryBuilder)
        query_builder.session = None

        repo = GraphQueryRepository(query_builder)
        result = repo.get_graph_statistics()
        assert result == {}
