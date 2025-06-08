import time
import streamlit as st
from streamlit_agraph import Node, Edge
from neo4j import RoutingControl


def execute_neo4j_query(driver, query, parameters=None):
    """Execute a Cypher query on Neo4j database with logging and timing"""
    st.session_state.last_cypher_query = query  # For LLM explanation

    try:
        start = time.time()

        records, _, _ = driver.execute_query(
            query,
            parameters or {},
            database_="neo4j",
            routing_=RoutingControl.READ,
        )

        elapsed = time.time() - start
        st.info(f"✅ Cypher query executed in {elapsed:.2f} seconds")

        return records

    except Exception as e:
        st.error("❌ Neo4j query failed")
        st.code(query, language='cypher')
        st.exception(e)
        return []


def convert_neo4j_to_graph(records):
    """Convert Neo4j query results to graph nodes and edges for visualization"""
    nodes = {}
    edges = []

    color_map = {
        "User": "#FF6B6B",
        "Question": "#4ECDC4",
        "Answer": "#45B7D1",
        "Tag": "#FFA62B",
        "Comment": "#C04CFD"
    }

    for idx, record in enumerate(records):
        # Handle scalar-only records (e.g., {'name': 'Jon', 'count': 5})
        if all(isinstance(v, (str, int, float)) for v in record.values()):
            label_str = ", ".join([f"{k}: {v}" for k, v in record.items()])
            node_id = f"record_{idx}"
            nodes[node_id] = Node(
                id=node_id,
                label="Result",
                size=30,
                color="#88C0D0",
                title=label_str
            )
        else:
            for key, value in record.items():
                # Handle node objects
                if hasattr(value, 'labels') and hasattr(value, 'id'):
                    node_id = str(value.id)
                    if node_id not in nodes:
                        label = list(value.labels)[0] if value.labels else "Node"
                        properties = dict(value.items()) if hasattr(value, 'items') else {}

                        display_label = properties.get("title") or properties.get("display_name") or properties.get("name") or label
                        display_label = f"{label}: {display_label[:20]}"

                        hover_text = properties.get("body_markdown") or properties.get("title") or ""
                        hover_text = hover_text[:200] + "..." if len(hover_text) > 200 else hover_text

                        nodes[node_id] = Node(
                            id=node_id,
                            label=display_label,
                            size=25,
                            color=color_map.get(label, "#4ECDC4"),
                            title=hover_text
                        )

                # Handle relationship objects
                elif hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'):
                    source_id = str(value.start_node.id)
                    target_id = str(value.end_node.id)
                    edge = Edge(
                        source=source_id,
                        target=target_id,
                        label=value.type,
                        color="#888"
                    )
                    edges.append(edge)

                # Handle scalar values mixed within records (e.g., individual count or name fields)
                elif isinstance(value, (str, int, float)):
                    node_id = f"{key}_{value}"
                    if node_id not in nodes:
                        nodes[node_id] = Node(
                            id=node_id,
                            label=f"{key}: {value}",
                            size=25,
                            color="#FFA62B",
                            title=str(value)
                        )

    # If no relationships but multiple scalar nodes exist, group them under a central hub node
    if nodes and not edges and len(nodes) > 1:
        center_id = "center_node"
        nodes[center_id] = Node(
            id=center_id,
            label="Query Results",
            size=35,
            color="#C04CFD",
            title="Grouped scalar values"
        )
        for nid in list(nodes.keys()):
            if nid != center_id:
                edges.append(Edge(source=center_id, target=nid, label="related"))

    return list(nodes.values()), edges
