# Neo4j Graph Database Integration

## Overview

This document describes the Neo4j graph database integration for the Hierarchical Device Data Dashboard. The integration provides graph-based hierarchy queries, path-finding algorithms, and efficient hierarchy traversal for the complete data hierarchy (Tenant → Customer → Site → Gateway → Device → User → DataStream).

## Architecture

### Components

1. **GraphDatabase** (`app/db/graph.py`)
   - Connection management for Neo4j
   - Schema creation with constraints and indexes
   - Graph initialization and cleanup

2. **GraphQueryBuilder** (`app/db/graph.py`)
   - Cypher query construction
   - Node and relationship creation
   - Hierarchy and path queries

3. **PathFindingAlgorithm** (`app/db/graph.py`)
   - Shortest path finding
   - All paths enumeration
   - Common ancestor detection
   - Ancestor/descendant traversal

4. **GraphSynchronizer** (`app/db/graph_sync.py`)
   - Synchronization between SQLite and Neo4j
   - Entity-level sync
   - Full data synchronization

5. **GraphHierarchyRepository** (`app/db/graph_repositories.py`)
   - High-level hierarchy queries
   - Path-to-root queries
   - Ancestor/descendant queries

6. **GraphQueryRepository** (`app/db/graph_repositories.py`)
   - Custom Cypher query execution
   - Node type queries
   - Graph statistics

## Graph Schema

### Node Types

- **Tenant**: Top-level organizational unit
- **Customer**: Customer account within a tenant
- **Site**: Physical or logical location within a customer
- **Gateway**: Edge computing device
- **Device**: Edge device connected to a gateway
- **User**: Individual user account
- **DataStream**: Continuous stream of metrics

### Relationship Types

- `HAS_CUSTOMER`: Tenant → Customer
- `HAS_SITE`: Customer → Site
- `HAS_GATEWAY`: Site → Gateway
- `HAS_DEVICE`: Gateway → Device
- `HAS_USER`: Site → User
- `HAS_DATA_STREAM`: Device → DataStream

### Constraints and Indexes

- Unique constraints on all node IDs
- Indexes on identifiers for fast lookups
- Indexes on status fields for filtering

## Usage Examples

### Initialize Graph Database

```python
from app.db.graph import GraphDatabase

# Create and connect to Neo4j
graph_db = GraphDatabase(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="password"
)
graph_db.connect()
graph_db.create_schema()
```

### Synchronize Data from SQLite to Neo4j

```python
from app.db.graph_sync import GraphSynchronizer
from app.db.database import get_db

sql_session = next(get_db())
sync = GraphSynchronizer(sql_session, graph_db)
sync.sync_all_data()
```

### Query Hierarchy

```python
from app.db.graph_repositories import GraphHierarchyRepository
from app.db.graph import GraphQueryBuilder, PathFindingAlgorithm

query_builder = GraphQueryBuilder(graph_db.session)
path_finder = PathFindingAlgorithm(graph_db.session)
repo = GraphHierarchyRepository(query_builder, path_finder)

# Get complete customer hierarchy
hierarchy = repo.get_customer_hierarchy("customer-id")

# Get children of a node
children = repo.get_children("site-id")

# Get parent of a node
parent = repo.get_parent("device-id")

# Get path between two nodes
path = repo.get_path_between_nodes("device-id", "customer-id")

# Get all descendants
descendants = repo.get_all_descendants("site-id")

# Get all ancestors
ancestors = repo.get_all_ancestors("device-id")

# Get common ancestor
ancestor = repo.get_common_ancestor("device-id-1", "device-id-2")
```

### Execute Custom Cypher Queries

```python
from app.db.graph_repositories import GraphQueryRepository

query_repo = GraphQueryRepository(query_builder)

# Get all devices with status "online"
devices = query_repo.get_nodes_by_property("Device", "status", "online")

# Count devices
count = query_repo.count_nodes_by_type("Device")

# Get graph statistics
stats = query_repo.get_graph_statistics()

# Execute custom Cypher query
result = query_repo.execute_cypher_query(
    "MATCH (c:Customer)-[:HAS_SITE]->(s:Site) WHERE c.id = $customerId RETURN s",
    {"customerId": "customer-id"}
)
```

## Performance Characteristics

### Query Performance

- **Shortest Path**: O(V + E) using breadth-first search
- **All Paths**: O(V + E) per path found
- **Hierarchy Query**: O(V + E) for complete hierarchy
- **Node Lookup**: O(1) with index on ID

### Scalability

- Supports up to 1 million devices
- Supports hierarchy depth up to 10 levels
- Efficient path-finding for large hierarchies
- Lazy loading for large result sets

## Fallback Strategy

If Neo4j is not available or not connected:

1. Graph operations return empty results or None
2. SQLite repositories continue to work
3. No errors are raised - graceful degradation
4. Logging indicates when graph operations are skipped

## Configuration

### Environment Variables

```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

### Docker Compose

```yaml
neo4j:
  image: neo4j:latest
  environment:
    NEO4J_AUTH: neo4j/password
  ports:
    - "7687:7687"
    - "7474:7474"
```

## Testing

### Unit Tests

```bash
python3 -m pytest app/tests/test_graph.py -v
python3 -m pytest app/tests/test_graph_sync.py -v
python3 -m pytest app/tests/test_graph_repositories.py -v
```

### Test Coverage

- GraphDatabase connection and schema creation
- GraphQueryBuilder node and relationship operations
- PathFindingAlgorithm path finding and traversal
- GraphSynchronizer data synchronization
- GraphHierarchyRepository hierarchy queries
- GraphQueryRepository custom queries

## API Integration

### Graph Query API Endpoints

```
POST /api/v2/graph/query
Body: {
  query: "MATCH (c:Customer)-[:HAS_SITE]->(s:Site) WHERE c.id = $customerId RETURN s",
  parameters: { customerId: "..." }
}
Response: GraphQueryResult

POST /api/v2/graph/pathfinding
Body: {
  from: { type: "Device", id: "..." },
  to: { type: "Customer", id: "..." }
}
Response: HierarchyPath[]

GET /api/v2/graph/hierarchy/{nodeId}
Response: HierarchyNode with children and relationships

GET /api/v2/graph/statistics
Response: GraphStatistics
```

## Limitations and Considerations

1. **Optional Component**: Neo4j is optional for MVP. SQLite repositories provide fallback.
2. **Synchronization**: Data must be explicitly synced from SQLite to Neo4j.
3. **Real-time Updates**: Graph updates are not automatic - requires manual sync or event-driven sync.
4. **Memory Usage**: Large hierarchies may require significant memory in Neo4j.
5. **Network Latency**: Remote Neo4j instances may have higher latency than local SQLite.

## Future Enhancements

1. **Event-Driven Sync**: Automatically sync changes from SQLite to Neo4j
2. **Caching**: Cache frequently accessed paths and hierarchies
3. **Query Optimization**: Use Neo4j query optimization for complex hierarchies
4. **Distributed Queries**: Support queries across multiple Neo4j instances
5. **Real-time Streaming**: Stream hierarchy changes to connected clients
6. **Graph Analytics**: Implement centrality and community detection algorithms

## Troubleshooting

### Connection Issues

```python
# Check if connected
if graph_db.is_connected():
    print("Connected to Neo4j")
else:
    print("Not connected to Neo4j")
```

### Schema Issues

```python
# Recreate schema
graph_db.clear_graph()
graph_db.create_schema()
```

### Sync Issues

```python
# Check sync status
sync = GraphSynchronizer(sql_session, graph_db)
sync.sync_all_data()  # Full resync
```

## References

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/api/python-driver/current/)
- [Cypher Query Language](https://neo4j.com/docs/cypher-manual/current/)
- [Graph Database Concepts](https://neo4j.com/docs/getting-started/current/)
