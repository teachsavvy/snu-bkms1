import streamlit as st
from openai import OpenAI
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import os
import requests
import json
from neo4j import GraphDatabase, RoutingControl

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'graph_utils')))
from graph_utils import execute_neo4j_query, convert_neo4j_to_graph

#def execute_neo4j_query(driver, query, parameters=None):
#    """Execute a Cypher query on Neo4j database"""
#    # Store the query in session state for context in AI responses
#    st.session_state.last_cypher_query = query
    
#    try:
#        records, _, _ = driver.execute_query(
#            query,
#            parameters or {},
#            database_="neo4j",
#            routing_=RoutingControl.READ,
#        )
#        return records
#    except Exception as e:
#        st.error(f"Neo4j query error: {str(e)}")
#        return []

def call_mcp_server(user_message):
    """Call MCP server to generate Cypher query"""
    try:
        # Replace with your actual MCP server endpoint
        mcp_endpoint = os.getenv("MCP_SERVER_ENDPOINT", "http://localhost:8000/generate-query")
        
        response = requests.post(
            mcp_endpoint,
            json={"message": user_message},
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("query", ""), data.get("parameters", {})
        else:
            st.error(f"MCP Server error: {response.status_code}")
            return "", {}
            
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling MCP server: {str(e)}")
        return "", {}

#def convert_neo4j_to_graph(records):
#    """Convert Neo4j query results to nodes and edges for visualization"""
#    nodes = {}
#    edges = []
    
#    # Node color mapping based on label
#    color_map = {
#        "User": "#FF6B6B",
#        "Question": "#4ECDC4",
#        "Answer": "#45B7D1",
#        "Tag": "#FFA62B",
#        "Comment": "#C04CFD"
#    }
    
#    # Process each record from the query results
#    for record in records:
#        # First pass: Extract all nodes
#        for key, value in record.items():
#            # Case 1: It's a Neo4j node object
#            if hasattr(value, 'labels') and hasattr(value, 'id'):
#                node_id = str(value.id)
#                if node_id not in nodes:
                    # Get the first label (e.g., 'User', 'Question')
#                   label = list(value.labels)[0] if value.labels else "Node"
#                    
#                    # Get properties to display in the label
#                    properties = {}
#                    if hasattr(value, 'items'):
#                        properties = dict(value.items())
#                    
#                    # Create a meaningful label
#                    display_label = label
#                    if 'name' in properties:
#                        display_label = f"{label}: {properties['name']}"
#                    elif 'display_name' in properties:
#                        display_label = f"{label}: {properties['display_name']}"
#                    elif 'title' in properties:
#                        display_label = f"{label}: {properties['title'][:20]}..."
#                    
#                    # Create hover text that includes body_markdown if available
#                    hover_text = ""
#                    if 'title' in properties:
#                        # Truncate long markdown to a reasonable length for hover
#                        title_text = properties['title']
#                        if len(title_text) > 200:
#                            title_text = title_text[:197] + "..."
#                        hover_text = title_text
#                    if 'body_markdown' in properties:
#                        # Truncate long markdown to a reasonable length for hover
#                        body_text = properties['body_markdown']
#                        if len(body_text) > 200:
#                            body_text = body_text[:197] + "..."
#                        hover_text = body_text
#                    
#                    # Create the node with appropriate color and hover text
#                    nodes[node_id] = Node(
#                        id=node_id,
#                        label=display_label,
#                        size=25,
#                        color=color_map.get(label, "#4ECDC4"),
#                        title=hover_text  # This is what shows on hover
#                    )
#            
#            # Case 2: It's a Neo4j relationship object
#            elif hasattr(value, 'type') and hasattr(value, 'start_node') and hasattr(value, 'end_node'):
#                source_id = str(value.start_node.id)
#                target_id = str(value.end_node.id)
#                
#                # Add source and target nodes if they don't exist yet
#                for node, node_id, node_obj in [("source", source_id, value.start_node), 
#                                               ("target", target_id, value.end_node)]:
#                    if node_id not in nodes and hasattr(node_obj, 'labels'):
#                        label = list(node_obj.labels)[0] if node_obj.labels else "Node"
#                        # Get properties to check for body_markdown
#                        properties = {}
#                        if hasattr(node_obj, 'items'):
#                            properties = dict(node_obj.items())
#                        
#                        # Create hover text
#                        hover_text = ""
#                        if 'body_markdown' in properties:
#                            body_text = properties['body_markdown']
#                            if len(body_text) > 200:
#                                body_text = body_text[:197] + "..."
#                            hover_text = body_text
#                        elif 'body' in properties:
#                            body_text = properties['body']
#                            if len(body_text) > 200:
#                                body_text = body_text[:197] + "..."
#                            hover_text = body_text
#                        
#                        nodes[node_id] = Node(
#                            id=node_id,
#                            label=f"{label}",
#                            size=25,
#                            color=color_map.get(label, "#4ECDC4"),
#                            title=hover_text
#                        )
#                
#                # Create the edge
#                edge = Edge(
#                    source=source_id,
#                    target=target_id,
#                    label=value.type,
#                    color="#999"
#                )
#                edges.append(edge)
#            
#            # Case 3: Handle scalar values (create nodes for them)
#            elif isinstance(value, (str, int, float)) and key not in ["count", "sum", "avg"]:
#                # For scalar results like usernames, create nodes for them
#                node_id = f"{key}_{value}"
#                if node_id not in nodes:
#                    # For scalar values, use the value itself as hover text if it's a string
#                    hover_text = str(value) if isinstance(value, str) else f"{key}: {value}"
#                    
#                    nodes[node_id] = Node(
#                        id=node_id,
#                        label=f"{key}: {value}",
#                        size=25,
#                        color="#FFA62B",
#                        title=hover_text
#                    )
#    
#    # If we only have scalar values and no relationships, create a central node
#    if nodes and not edges and len(nodes) > 1:
#        central_id = "results_center"
#        nodes[central_id] = Node(
#            id=central_id,
#            label="Results",
#            size=30,
#            color="#C04CFD",
#            title="Central node connecting all query results"
#        )
#        
#        # Connect all nodes to the central node
#        for node_id in list(nodes.keys()):
#            if node_id != central_id:
#                edges.append(Edge(
#                    source=central_id,
#                    target=node_id,
#                    label="result",
#                    color="#CCCCCC"
#                ))
#    
#    return list(nodes.values()), edges

def display_network_in_chat(nodes, edges):
    """Display network visualization inside chat message"""
    # Configuration for the graph
    config = Config(
        width=700,
        height=400,
        directed=True,
        physics=True,
        physics_props={
            "barnesHut": {"gravitationalConstant": -2000, "centralGravity": 0.3, "springLength": 95},
            "minVelocity": 0.75
        },
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
        node={
            "labelProperty": "label",
            "fontColor": "black",
            "fontSize": 14,
            "highlightFontSize": 16,
            "highlightStrokeColor": "#FF0000",
            "highlightStrokeWidth": 2
        },
        link={
            "labelProperty": "label",
            "renderLabel": True,
            "fontSize": 12,
            "highlightColor": "#FF0000"
        }
    )
    
    # Display the graph
    st.subheader("📊 Network Visualization")
    return_value = agraph(nodes=nodes, edges=edges, config=config)
    
    # Display selected node information
    if return_value:
        st.write("**Selected Node:**", return_value)

def clean_messages_for_api(messages):
    """Clean messages to ensure they are JSON serializable for the API"""
    cleaned_messages = []
    
    for msg in messages:
        # Create a new message with only the essential fields
        cleaned_msg = {
            "role": msg["role"],
            "content": msg["content"]
        }
        cleaned_messages.append(cleaned_msg)
    
    return cleaned_messages

def stream_openai_response(client, messages):
    """Stream response from OpenAI API"""
    try:
        # Clean messages to ensure they are JSON serializable
        api_messages = clean_messages_for_api(messages)
        
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=api_messages,
            max_tokens=500,
            temperature=0.7,
            stream=True
        )
        
        response_placeholder = st.empty()
        full_response = ""
        
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                full_response += chunk.choices[0].delta.content
                response_placeholder.markdown(full_response + "▌")
        
        response_placeholder.markdown(full_response)
        return full_response
        
    except Exception as e:
        st.error(f"Error streaming from OpenAI: {str(e)}")
        return "Sorry, I encountered an error while generating the response."

# Load environment variables
load_dotenv()

# Database and API configurations
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_AUTH = (os.getenv("NEO4J_AUTH_USERNAME"), os.getenv("NEO4J_AUTH_PASSWORD"))
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

st.set_page_config(
    page_title="GraphRAG Chatbot with Stack Overflow",
    page_icon="https://cdn.sstatic.net/Sites/stackoverflow/company/img/logos/so/so-icon.png",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sidebar with API status
st.sidebar.header("🔧 Configuration Status")

# Check API configurations in sidebar
if not api_key:
    st.sidebar.error("⚠️ OpenAI API key not found!")
else:
    st.sidebar.success("✅ OpenAI API key loaded")

if not NEO4J_URI:
    st.sidebar.error("⚠️ Neo4j connection not configured!")
else:
    st.sidebar.success("✅ Neo4j connection configured")

# Sidebar info
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Environment Variables Required:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `NEO4J_URI`: Neo4j database URI
- `NEO4J_AUTH_USERNAME`: Neo4j username
- `NEO4J_AUTH_PASSWORD`: Neo4j password
- `MCP_SERVER_ENDPOINT`: MCP server endpoint
""")

# Main content
st.image("https://stackoverflow.design/assets/img/logos/so/logo-stackoverflow.png", width=200)
st.title("🤖 GraphRAG Chatbot for Searching")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Clear chat button
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

# Display all chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant" and "network_data" in message:
            # Display the text response first
            st.markdown(message["content"])
            
            # Then display the network visualization
            nodes, edges = message["network_data"]["nodes"], message["network_data"]["edges"]
            display_network_in_chat(nodes, edges)
            
            # Display query results details
            if "query_results" in message:
                with st.expander("📋 View Detailed Query Results", expanded=False):
                    results = message["query_results"]
                    for i, record in enumerate(results):
                        st.markdown(f"**Result {i+1}**")
                        for key, value in record.items():
                            if hasattr(value, 'labels') and hasattr(value, 'element_id'):  # It's a node
                                label = list(value.labels)[0] if value.labels else "Node"
                                properties = dict(value.items()) if hasattr(value, 'items') else {}
                                st.markdown(f"**{key}** ({label})")
                                st.json(properties)
                            elif hasattr(value, 'type') and hasattr(value, 'start_node'):  # It's a relationship
                                st.markdown(f"**{key}** (Relationship: {value.type})")
                            else:  # It's a scalar value
                                st.markdown(f"**{key}**: {value}")
                        st.markdown("---")
        else:
            st.markdown(message["content"])

# Show info message only if no messages exist
if not st.session_state.messages:
    st.info("💭 Start a conversation! Ask me about network data or any other topic.")

# Chat input
if prompt := st.chat_input("Ask me anything about the network or any other topic..."):
    # Add user message to chat history and display immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display the user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Process the message
    if api_key and NEO4J_URI:
        try:
            with st.chat_message("assistant"):
                # Step 1: Call MCP server to generate Cypher query
                with st.spinner("🔍 Generating database query..."):
                    cipher_query, query_params = call_mcp_server(prompt)
                    
                    query_results = None
                    nodes = None
                    edges = None
                    
                    if cipher_query:
                        st.info(f"Generated query: `{cipher_query}`")
                        
                        # Step 2: Execute query on Neo4j
                        with st.spinner("📊 Querying database..."):
                            with GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH) as driver:
                                driver.verify_connectivity()
                                query_results = execute_neo4j_query(driver, cipher_query, query_params)
                                
                                if query_results:
                                    st.success(f"Found {len(query_results)} results")
                                    
                                    # Step 3: Convert results to graph visualization
                                    nodes, edges = convert_neo4j_to_graph(query_results)

                                    # ✅ 디버깅 로그 추가
                                    st.write("🧪 nodes:", len(nodes), "edges:", len(edges))

                                    # 제안된 조건
                                    if nodes or edges:
                                        st.success("📈 Network visualization generated!")
                                        st.session_state.messages[-1]["network_data"] = {"nodes": nodes, "edges": edges}
                                    else:
                                        st.warning("No graph data found in query results")
                                else:
                                    st.warning("No results found for the query")
                    else:
                        st.warning("Could not generate a valid database query")
                
                # Step 4: Generate OpenAI response (streaming) with query results context
                with st.spinner("🤖 Generating response..."):
                    # Create a system message that includes query results if available
                    system_content = "You are a helpful assistant that can discuss network graphs, database queries, data visualization, and any other topics. You have access to a Neo4j database and can help analyze graph data."
                    
                    # If we have query results, add them to the system message
                    if query_results:
                        results_summary = []
                        
                        # Format the query results for the system message
                        for i, record in enumerate(query_results[:5]):  # Limit to first 5 results to avoid token limits
                            record_summary = {}
                            for key, value in record.items():
                                # Handle different types of values
                                if hasattr(value, 'labels') and hasattr(value, 'element_id'):
                                    # It's a node
                                    label = list(value.labels)[0] if value.labels else "Node"
                                    properties = dict(value.items()) if hasattr(value, 'items') else {}
                                    record_summary[key] = f"{label} with properties: {properties}"
                                elif hasattr(value, 'type') and hasattr(value, 'start_node'):
                                    # It's a relationship
                                    record_summary[key] = f"Relationship of type {value.type}"
                                else:
                                    # It's a scalar value
                                    record_summary[key] = str(value)
                            results_summary.append(record_summary)
                        
                        # Add query results context to system message
                        if results_summary:
                            system_content += f"\n\nThe following query results were retrieved from the Neo4j database:\n{results_summary}\n\nPlease incorporate these results in your response when relevant. Explain insights from the data when possible."
                        
                        # Add the Cypher query that was executed
                        if "last_cypher_query" in st.session_state:
                            system_content += f"\n\nThe Cypher query that was executed was:\n```\n{st.session_state.last_cypher_query}\n```"
                    
                    system_message = {
                        "role": "system", 
                        "content": system_content
                    }
                    
                    messages_for_ai = [system_message] + st.session_state.messages
                    assistant_response = stream_openai_response(client, messages_for_ai)
                    
                    # Create assistant message with network data if available
                    assistant_message = {"role": "assistant", "content": assistant_response}
                    
                    # Add network visualization data to the message if we have it
                    if nodes and edges:
                        assistant_message["network_data"] = {"nodes": nodes, "edges": edges}
                        assistant_message["query_results"] = query_results
                        display_network_in_chat(nodes, edges)
                        
                        # Display query results details
                        if query_results:
                            with st.expander("📋 View Detailed Query Results", expanded=False):
                                for i, record in enumerate(query_results):
                                    st.markdown(f"**Result {i+1}**")
                                    for key, value in record.items():
                                        if hasattr(value, 'labels') and hasattr(value, 'element_id'):  # It's a node
                                            label = list(value.labels)[0] if value.labels else "Node"
                                            properties = dict(value.items()) if hasattr(value, 'items') else {}
                                            st.markdown(f"**{key}** ({label})")
                                            st.json(properties)
                                        elif hasattr(value, 'type') and hasattr(value, 'start_node'):  # It's a relationship
                                            st.markdown(f"**{key}** (Relationship: {value.type})")
                                        else:  # It's a scalar value
                                            st.markdown(f"**{key}**: {value}")
                                    st.markdown("---")
                    
                    # Add assistant response to chat history
                    st.session_state.messages.append(assistant_message)
                        
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            with st.chat_message("assistant"):
                st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})
    else:
        error_msg = "Cannot respond: Required API keys or database connection not configured"
        with st.chat_message("assistant"):
            st.error(error_msg)
        st.session_state.messages.append({"role": "assistant", "content": error_msg})
