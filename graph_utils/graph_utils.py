import time
import streamlit as st
from streamlit_agraph import Node, Edge
from neo4j import RoutingControl

def execute_neo4j_query(driver, query, parameters=None):
    """Execute a Cypher query on Neo4j database with logging and timing"""
    # Store the last executed query for LLM explanations
    st.session_state.last_cypher_query = query
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
    """Convert Neo4j query results to Streamlit-agraph nodes and edges.
    Any relationships returned by the query are used directly. When a record
    contains only nodes, simple heuristics create edges between Users, Questions,
    Answers, Tags and Comments based on the Stack Overflow schema. This keeps
    the visualization connected even if the Cypher query omitted relationships.
    """
    nodes = {}
    edges = []
    edge_set = set()

    # Visual distinction for different node labels
    color_map = {
        "User": "#FF6B6B",
        "Question": "#4ECDC4",
        "Answer": "#45B7D1",
        "Tag": "#FFA62B",
        "Comment": "#C04CFD"
    }
    # Iterate over each record and create corresponding nodes/edges
    for idx, record in enumerate(records):
        if all(isinstance(v, (str, int, float)) for v in record.values()):
            label_str = ", ".join(f"{k}: {v}" for k, v in record.items())
            label_keys = [
                k for k in record
                if isinstance(k, str) and ("name" in k.lower() or "title" in k.lower())
            ]
            display_label = str(record[label_keys[0]]) if label_keys else "Result"
            node_id = f"record_{idx}"
            nodes[node_id] = Node(
                id=node_id,
                label=display_label[:30],
                size=30,
                color="#88C0D0",
                title=label_str,
            )
        else:
            for key, value in record.items():
                if hasattr(value, "labels") and hasattr(value, "id"):
                    node_id = str(value.id)
                    properties = dict(value.items()) if hasattr(value, "items") else {}
                    if node_id not in nodes:
                        label = list(value.labels)[0] if value.labels else "Node"
                        display_label = (
                            properties.get("title")
                            or properties.get("display_name")
                            or properties.get("name")
                            or label
                        )
                        display_label = f"{label}: {display_label[:20]}"
                        hover_text = properties.get("body_markdown") or properties.get("title") or ""
                        hover_text = hover_text[:200] + "..." if len(hover_text) > 200 else hover_text
                        node_obj = Node(
                            id=node_id,
                            label=display_label,
                            size=25,
                            color=color_map.get(label, "#4ECDC4"),
                            title=hover_text,
                        )
                        nodes[node_id] = node_obj
                    else:
                        node_obj = nodes[node_id]
                    # Store full Neo4j properties for display when selected
                    setattr(node_obj, "properties", properties)

                elif (
                    hasattr(value, "type")
                    and hasattr(value, "start_node")
                    and hasattr(value, "end_node")
                ):
                    start_node = value.start_node
                    end_node = value.end_node
                    for node in (start_node, end_node):
                        n_id = str(node.id)
                        props = (
                            dict(node.items()) if hasattr(node, "items") else {}
                        )
                        if n_id not in nodes:
                            label = list(node.labels)[0] if node.labels else "Node"
                            disp_label = (
                                props.get("title")
                                or props.get("display_name")
                                or props.get("name")
                                or label
                            )
                            disp_label = f"{label}: {disp_label[:20]}"
                            hover = props.get("body_markdown") or props.get("title") or ""
                            hover = hover[:200] + "..." if len(hover) > 200 else hover
                            node_obj = Node(
                                id=n_id,
                                label=disp_label,
                                size=25,
                                color=color_map.get(label, "#4ECDC4"),
                                title=hover,
                            )
                            nodes[n_id] = node_obj
                        else:
                            node_obj = nodes[n_id]

                        setattr(node_obj, "properties", props)

                    source_id = str(start_node.id)
                    target_id = str(end_node.id)

                    # Skip self-edges
                    if source_id != target_id:
                        edge_key = (source_id, target_id, value.type)

                        if edge_key not in edge_set:
                            edge_set.add(edge_key)
                            edges.append(
                                Edge(
                                    source=source_id,
                                    target=target_id,
                                    label=value.type,
                                    color="#888",
                                )
                            )

    return list(nodes.values()), edges