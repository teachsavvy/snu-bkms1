import streamlit as st
from openai import OpenAI
from streamlit_agraph import agraph, Node, Edge, Config
from dotenv import load_dotenv
import os
import requests
import json
from neo4j import GraphDatabase, RoutingControl
import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'graph_utils')))
from graph_utils import execute_neo4j_query, convert_neo4j_to_graph
def show_node_properties(props):
    """Display node properties with a stylized title when available."""
    title = props.get("title") or props.get("display_name") or props.get("name")
    link = props.get("link")
    rest = {k: v for k, v in props.items() if k not in {"title", "display_name", "name", "link"}}
    if title and link:
        st.markdown(
            f"<h5 style='margin-bottom:0'><a href='{link}' target='_blank'>{title}</a></h5>",
            unsafe_allow_html=True,
        )
    elif title:
        st.markdown(f"**{title}**")
    if rest:
        st.json(rest)
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
def display_network_in_chat(nodes, edges):
    """Display network visualization with a node detail panel"""
    config = Config(
        width=1000,
        height=600,
        directed=True,
        physics=True,
        physics_props={
            "barnesHut": {
                "gravitationalConstant": -30000,  # 노드 간 척력 증가
                "centralGravity": 0.1,
                "springLength": 400,  # 엣지 길이 증가
                "springConstant": 0.05,
                "damping": 0.05,
                "avoidOverlap": 1
            },
            "minVelocity": 0.75
        },
        staticGraphWithDragAndDrop=False,
        hierarchical=True,
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
            "highlightColor": "#FF0000",
            "linkDirectionalArrowLength": 20
        }
    )

    st.subheader("📊 Network Visualization")
    col_graph, col_info = st.columns([2, 1])
    with col_graph:
        selected = agraph(nodes=nodes, edges=edges, config=config)
    # Build a lookup from node ID to stored properties so we can
    # show details even if the selected value is just the ID
    node_lookup = {str(n.id): getattr(n, "properties", {}) for n in nodes}
    with col_info:
        st.subheader("🛈 Selected Node")
        if selected:
            try:
                import dataclasses
                if dataclasses.is_dataclass(selected):
                    props = getattr(selected, "properties", None)
                    if props:
                        show_node_properties(props)
                    else:
                        data = dataclasses.asdict(selected)
                        show_node_properties(data)
                elif isinstance(selected, (str, int)):
                    props = node_lookup.get(str(selected))
                    if props:
                        show_node_properties(props)
                    else:
                        st.write(selected)
                elif isinstance(selected, dict):
                    props = selected.get("properties", selected)
                    show_node_properties(props)
                else:
                    st.write(selected)
            except Exception:
                st.write(selected)
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
            model="gpt-4o-mini",
            messages=api_messages,
            max_tokens=500,
            temperature=0.2,
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
st.title("🤖 GDBMS-Related Knowledge Retrieval Based on GraphRAG")
# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Clear chat button - displayed as a floating button using simple CSS
clear_container = st.empty()
if clear_container.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()

st.markdown(
    """
    <style>
        .stButton>button {
            position: fixed;
            bottom: 10px;
            right: 80px;
            z-index: 1000;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

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
                            if hasattr(value, 'labels') and hasattr(value, 'element_id'):
                                label = list(value.labels)[0] if value.labels else 'Node'
                                properties = dict(value.items()) if hasattr(value, 'items') else {}
                                st.markdown(f"**{key}** ({label})")
                                show_node_properties(properties)
                            elif hasattr(value, 'type') and hasattr(value, 'start_node'):
                                st.markdown(f"**{key}** (Relationship: {value.type})")
                            else:
                                st.markdown(f"**{key}**: {value}")
                        st.markdown("---")
        else:
            st.markdown(message["content"])
# Show info message only if no messages exist
if not st.session_state.messages:
    st.info("💭 그래프 데이터베이스 관련 지식을 물어보세요!")
# Chat input
if prompt := st.chat_input("여기에 질문하세요"):
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
                    nodes = []
                    edges = []

                    if cipher_query:
                        # 쿼리문을 화면에 표시
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
                                    st.write(f"🧪 nodes: {len(nodes)}, edges: {len(edges)}")
                                else:
                                    st.warning("No results found for the query")
                    else:
                        st.warning("Could not generate a valid database query")

                # --- [수정됨] 노드 개수에 따라 AI 요약 여부 결정 ---
                # Step 4: Generate response (AI summary or placeholder text)
                assistant_response = ""
                if len(nodes) >= 25:
                    # 노드가 25개 이상이면 AI 요약을 건너뛰고 안내 문구 표시
                    assistant_response = "결과가 너무 많아(25개 이상) 요약을 생략하고 그래프만 표시합니다."
                    st.markdown(assistant_response)
                elif not query_results:
                    # 쿼리 결과가 없을 때의 기본 답변
                    assistant_response = "해당 질문에는 답할 수 없습니다" # <--- 사용자 요청 문구로 수정됨
                    st.markdown(assistant_response)
                else:
                    # 노드가 25개 미만이면 기존과 같이 AI 요약 생성
                    with st.spinner("🤖 Generating response..."):
                        system_content = "You are a helpful assistant that can discuss network graphs, database queries, data visualization, and any other topics. You have access to a Neo4j database and can help analyze graph data."
                        
                        if query_results:
                            results_summary = []
                            for i, record in enumerate(query_results[:5]):
                                record_summary = {}
                                for key, value in record.items():
                                    if hasattr(value, 'labels') and hasattr(value, 'element_id'):
                                        label = list(value.labels)[0] if value.labels else "Node"
                                        properties = dict(value.items()) if hasattr(value, 'items') else {}
                                        if 'creation_date' in properties and isinstance(properties['creation_date'], (int, float)):
                                            try:
                                                ts = properties['creation_date']
                                                properties['creation_date'] = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                                            except Exception: pass
                                        properties.pop('uuid', None)
                                        properties.pop('body_markdown', None)
                                        record_summary[key] = f"{label} with properties: {properties}"
                                    elif hasattr(value, 'type') and hasattr(value, 'start_node'):
                                        record_summary[key] = f"Relationship of type {value.type}"
                                    else: record_summary[key] = str(value)
                                results_summary.append(record_summary)
                            
                            if results_summary:
                                system_content += f"\n\nThe following query results were retrieved from the Neo4j database:\n{results_summary}\n\nBased ONLY on these results, answer the user's question factually and concisely. Do not add any interpretation, speculation, or analysis."

                        system_message = {"role": "system", "content": system_content}
                        messages_for_ai = [system_message] + st.session_state.messages
                        assistant_response = stream_openai_response(client, messages_for_ai)

                # --- [수정됨] 공통 로직으로 메시지 생성 및 그래프/결과 표시 ---
                # Create the final assistant message dictionary
                assistant_message = {"role": "assistant", "content": assistant_response}

                # Add network visualization and query results data to the message
                if nodes:
                    assistant_message["network_data"] = {"nodes": nodes, "edges": edges}
                    assistant_message["query_results"] = query_results
                    display_network_in_chat(nodes, edges)

                    if query_results:
                        # expander 제목을 고유하게 변경
                        with st.expander("📋 View Detailed Query Results (Current)", expanded=False):
                            for i, record in enumerate(query_results):
                                st.markdown(f"**Result {i+1}**")
                                for key, value in record.items():
                                    if hasattr(value, 'labels') and hasattr(value, 'element_id'):
                                        label = list(value.labels)[0] if value.labels else 'Node'
                                        properties = dict(value.items()) if hasattr(value, 'items') else {}
                                        st.markdown(f"**{key}** ({label})")
                                        show_node_properties(properties)
                                    elif hasattr(value, 'type') and hasattr(value, 'start_node'):
                                        st.markdown(f"**{key}** (Relationship: {value.type})")
                                    else:
                                        st.markdown(f"**{key}**: {value}")
                                st.markdown("---")
                
                # Add the complete assistant response to chat history
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