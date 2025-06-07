import streamlit as st
from openai import OpenAI
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import os
import requests
import json
from neo4j import GraphDatabase, RoutingControl

def execute_neo4j_query(driver, query, parameters=None):
    """Execute a Cypher query on Neo4j database"""
    try:
        records, _, _ = driver.execute_query(
            query,
            parameters or {},
            database_="neo4j",
            routing_=RoutingControl.READ,
        )
        return records
    except Exception as e:
        st.error(f"Neo4j query error: {str(e)}")
        return []

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

def convert_neo4j_to_graph(records):
    """Convert Neo4j query results to nodes and edges for visualization"""
    nodes = {}
    edges = []
    
    for record in records:
        # Extract nodes from the record
        for key, value in record.items():
            if hasattr(value, 'labels') and hasattr(value, 'id'):  # It's a node
                node_id = str(value.id)
                if node_id not in nodes:
                    label = list(value.labels)[0] if value.labels else "Node"
                    nodes[node_id] = Node(
                        id=node_id,
                        label=f"{label}:{node_id}",
                        size=25,
                        color="#4ECDC4"
                    )
            elif hasattr(value, 'type') and hasattr(value, 'start_node'):  # It's a relationship
                edge = Edge(
                    source=str(value.start_node.id),
                    target=str(value.end_node.id),
                    label=value.type,
                    color="#999"
                )
                edges.append(edge)
    
    return list(nodes.values()), edges

def stream_openai_response(client, messages):
    """Stream response from OpenAI API"""
    try:
        stream = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
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

# Page configuration
st.set_page_config(
    page_title="Network Visualization & AI Chat",
    page_icon="🤖",
    layout="wide"
)

st.title("🕸️ Network Visualization & AI Chatbot")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "graph_nodes" not in st.session_state:
    st.session_state.graph_nodes = [
        Node(id="A", label="Node A", size=25, color="#FF6B6B"),
        Node(id="B", label="Node B", size=25, color="#4ECDC4"),
        Node(id="C", label="Node C", size=25, color="#45B7D1"),
    ]
if "graph_edges" not in st.session_state:
    st.session_state.graph_edges = [
        Edge(source="A", target="B", label="A-B", color="#999"),
        Edge(source="B", target="C", label="B-C", color="#999"),
    ]

# Create two columns
col1, col2 = st.columns([1, 1])

# Left column: Network Visualization
with col1:
    st.header("🕸️ Network Graph")
    
    # Configuration for the graph
    config = Config(
        width=500,
        height=400,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False,
    )
    
    # Display the graph
    return_value = agraph(
        nodes=st.session_state.graph_nodes, 
        edges=st.session_state.graph_edges, 
        config=config
    )
    
    # Display selected node information
    if return_value:
        st.write("**Selected Node:**", return_value)
    
    # Add controls to modify the graph
    st.subheader("Graph Controls")
    
    if st.button("Reset Graph"):
        st.session_state.graph_nodes = [
            Node(id="A", label="Node A", size=25, color="#FF6B6B"),
            Node(id="B", label="Node B", size=25, color="#4ECDC4"),
            Node(id="C", label="Node C", size=25, color="#45B7D1"),
        ]
        st.session_state.graph_edges = [
            Edge(source="A", target="B", label="A-B", color="#999"),
            Edge(source="B", target="C", label="B-C", color="#999"),
        ]
        st.rerun()

# Right column: OpenAI Chatbot
with col2:
    st.header("🤖 AI Assistant")
    
    # Check API configurations
    if not api_key:
        st.error("⚠️ OpenAI API key not found! Please add OPENAI_API_KEY to your .env file")
    else:
        st.success("✅ OpenAI API key loaded")
    
    if not NEO4J_URI:
        st.error("⚠️ Neo4j URI not found! Please add NEO4J_URI to your .env file")
    else:
        st.success("✅ Neo4j connection configured")
    
    # Display chat messages ABOVE the input box
    chat_container = st.container()
    with chat_container:
        if st.session_state.messages:
            for i, message in enumerate(st.session_state.messages):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        else:
            st.info("💭 Start a conversation! Ask me about network data or any other topic.")
    
    # Clear chat button (placed before input)
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()
    
    # Chat input at the bottom
    if prompt := st.chat_input("Ask me anything about the network or any other topic..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Process the message
        if api_key and NEO4J_URI:
            try:
                with st.chat_message("assistant"):
                    with st.spinner("🔍 Generating database query..."):
                        # Step 1: Call MCP server to generate Cypher query
                        cipher_query, query_params = call_mcp_server(prompt)
                        
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
                                        if nodes:
                                            st.session_state.graph_nodes = nodes
                                            st.session_state.graph_edges = edges
                                            st.success("📈 Graph updated with query results!")
                                        else:
                                            st.warning("No graph data found in query results")
                                    else:
                                        st.warning("No results found for the query")
                        else:
                            st.warning("Could not generate a valid database query")
                    
                    # Step 4: Generate OpenAI response (streaming)
                    with st.spinner("🤖 Generating response..."):
                        system_message = {
                            "role": "system", 
                            "content": "You are a helpful assistant that can discuss network graphs, database queries, data visualization, and any other topics. You have access to a Neo4j database and can help analyze graph data."
                        }
                        
                        messages_for_ai = [system_message] + st.session_state.messages
                        assistant_response = stream_openai_response(client, messages_for_ai)
                        
                        # Add assistant response to chat history
                        st.session_state.messages.append({"role": "assistant", "content": assistant_response})
                        
            except Exception as e:
                st.error(f"Error processing message: {str(e)}")
        else:
            with st.chat_message("assistant"):
                st.error("Cannot respond: Required API keys or database connection not configured")

# Footer
st.markdown("---")
st.markdown("""
**Environment Variables Required:**
- `OPENAI_API_KEY`: Your OpenAI API key
- `NEO4J_URI`: Neo4j database URI (e.g., "neo4j://localhost:7687")
- `NEO4J_AUTH_USERNAME`: Neo4j username
- `NEO4J_AUTH_PASSWORD`: Neo4j password
- `MCP_SERVER_ENDPOINT`: MCP server endpoint (optional, defaults to localhost:8000)

**Instructions:**
1. Install: `pip install streamlit streamlit-agraph openai python-dotenv neo4j requests`
2. Create `.env` file with the variables above
3. Run: `streamlit run app.py`
""")