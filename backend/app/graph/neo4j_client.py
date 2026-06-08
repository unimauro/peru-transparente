"""Cliente Neo4j para el grafo de poder."""
from neo4j import AsyncGraphDatabase

from app.core.config import get_settings

settings = get_settings()
_driver = AsyncGraphDatabase.driver(
    settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password)
)


async def get_neighborhood(node_id: str, depth: int = 2, limit: int = 300) -> dict:
    """Vecindario de un nodo para la vista de grafo (acotado por profundidad y límite)."""
    depth = max(1, min(depth, 3))  # nunca más de 3 saltos en vivo
    query = (
        "MATCH path = (n {id: $id})-[*1.." + str(depth) + "]-(m) "
        "RETURN path LIMIT $limit"
    )
    async with _driver.session() as session:
        result = await session.run(query, id=node_id, limit=limit)
        nodes: dict[str, dict] = {}
        edges: list[dict] = []
        async for record in result:
            for node in record["path"].nodes:
                nodes[node["id"]] = {
                    "id": node["id"],
                    "label": list(node.labels)[0] if node.labels else "Node",
                    "name": node.get("name") or node.get("title"),
                    "confidence": node.get("confidence"),
                }
            for rel in record["path"].relationships:
                edges.append(
                    {
                        "source": rel.start_node["id"],
                        "target": rel.end_node["id"],
                        "type": rel.type,
                        "hypothesis": rel.type.startswith("POSSIBLE"),
                    }
                )
    return {"nodes": list(nodes.values()), "edges": edges}


async def shortest_path(a_id: str, b_id: str, max_len: int = 6) -> dict:
    """Ruta de poder más corta entre dos nodos."""
    query = (
        "MATCH p = shortestPath((a {id:$a})-[*.." + str(max_len) + "]-(b {id:$b})) "
        "RETURN p"
    )
    async with _driver.session() as session:
        result = await session.run(query, a=a_id, b=b_id)
        record = await result.single()
        if not record:
            return {"nodes": [], "edges": []}
        path = record["p"]
        nodes = [
            {"id": n["id"], "label": list(n.labels)[0] if n.labels else "Node",
             "name": n.get("name") or n.get("title")}
            for n in path.nodes
        ]
        edges = [
            {"source": r.start_node["id"], "target": r.end_node["id"], "type": r.type}
            for r in path.relationships
        ]
    return {"nodes": nodes, "edges": edges}


async def close() -> None:
    await _driver.close()
