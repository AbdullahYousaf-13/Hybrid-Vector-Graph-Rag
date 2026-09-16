"""
Export/import the whole graph (nodes, relationships, and embedding vectors)
to a local JSON file, so a dataset (e.g. the Napoleon corpus) can be fully
wiped and later restored WITHOUT re-calling the embedding API.

Node keys used to re-MERGE on import (must match KG/kg.py's ingestion keys):
    Chunk   -> chunkId
    Section -> (type, parent_name)
    Person  -> name
    Event   -> name
"""

import json
from pathlib import Path

NODE_LABELS = ["Chunk", "Section", "Person", "Event"]


def _node_key(label: str, props: dict) -> dict:
    """The property (or properties) that uniquely identify a node of this label."""
    if label == "Chunk":
        return {"chunkId": props["chunkId"]}
    if label == "Section":
        return {"type": props["type"], "parent_name": props["parent_name"]}
    # Person, Event
    return {"name": props["name"]}


def export_graph(graph, out_path: str) -> dict:
    """
    Reads every node (by label) and every relationship in the graph and
    writes them to `out_path` as JSON. Read-only - does not modify the DB.
    Returns a small summary dict of what was exported.
    """
    data = {"nodes": {}, "relationships": []}

    for label in NODE_LABELS:
        rows = graph.query(f"MATCH (n:{label}) RETURN properties(n) AS props")
        data["nodes"][label] = [row["props"] for row in rows]

    rel_rows = graph.query(
        """
        MATCH (a)-[r]->(b)
        RETURN labels(a)[0] AS aLabel, properties(a) AS aProps,
               type(r) AS relType,
               labels(b)[0] AS bLabel, properties(b) AS bProps
        """
    )
    for row in rel_rows:
        data["relationships"].append({
            "aLabel": row["aLabel"], "aKey": _node_key(row["aLabel"], row["aProps"]),
            "relType": row["relType"],
            "bLabel": row["bLabel"], "bKey": _node_key(row["bLabel"], row["bProps"]),
        })

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")

    summary = {label: len(nodes) for label, nodes in data["nodes"].items()}
    summary["relationships"] = len(data["relationships"])
    return summary


def wipe_graph(graph, index_name: str = "Chunk") -> None:
    """Deletes ALL nodes/relationships and drops the vector index. Irreversible
    unless you've exported first."""
    graph.query("MATCH (n) DETACH DELETE n")
    graph.query(f"DROP INDEX {index_name} IF EXISTS")


def import_graph(graph, in_path: str) -> dict:
    """
    Re-creates nodes (with their saved textEmbedding vectors, no API calls)
    and relationships from a file written by export_graph(). MERGEs on the
    same natural keys used at ingestion time, so it's safe to re-run.
    """
    data = json.loads(Path(in_path).read_text(encoding="utf-8"))

    for label, nodes in data["nodes"].items():
        for props in nodes:
            embedding = props.pop("textEmbedding", None)
            graph.query(
                f"MERGE (n:{label} {{ {', '.join(f'{k}: ${k}' for k in props)} }}) "
                f"SET n += $props",
                params={**props, "props": props},
            )
            if embedding is not None:
                key = _node_key(label, props)
                where = " AND ".join(f"n.{k} = $key.{k}" for k in key)
                graph.query(
                    f"MATCH (n:{label}) WHERE {where} "
                    f"CALL db.create.setNodeVectorProperty(n, 'textEmbedding', $embedding) RETURN n",
                    params={"key": key, "embedding": embedding},
                )

    for rel in data["relationships"]:
        a_where = " AND ".join(f"a.{k} = $aKey.{k}" for k in rel["aKey"])
        b_where = " AND ".join(f"b.{k} = $bKey.{k}" for k in rel["bKey"])
        graph.query(
            f"""
            MATCH (a:{rel['aLabel']}), (b:{rel['bLabel']})
            WHERE {a_where} AND {b_where}
            MERGE (a)-[:{rel['relType']}]->(b)
            """,
            params={"aKey": rel["aKey"], "bKey": rel["bKey"]},
        )

    summary = {label: len(nodes) for label, nodes in data["nodes"].items()}
    summary["relationships"] = len(data["relationships"])
    return summary
