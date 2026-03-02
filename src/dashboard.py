import streamlit as st
import sys
import os

# Add the parent directory to the path so we can import our agents module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.orchestrator import audit_graph
from agents.cartographer import process_document

st.set_page_config(page_title="Sentinel-Graph Enterprise Auditor", layout="wide")

st.title("🛡️ Sentinel-Graph Agentic Auditor")
st.markdown("Navigate complex enterprise graphs using Agentic Multi-Hop reasoning and Self-RAG.")

# Sidebar for Knowledge Injection
with st.sidebar:
    st.header("🧠 The Cartographer")
    st.markdown("Inject new documents into Neo4j via Specialist A.")
    new_doc = st.text_area("Audit Document / Knowledge:", height=150)
    if st.button("Process & Map Entities"):
        with st.spinner("Extracting Entities and Mapping to Graph..."):
            try:
                res = process_document(new_doc)
                st.success(f"Extracted {len(res.entities)} Entities and {len(res.relationships)} Relationships!")
                st.json(res.model_dump())
            except Exception as e:
                st.error(f"Failed: {str(e)}")

# Main Query Section
st.header("🔍 The Detective & Auditor")
query = st.text_input("Enter Audit Question:", placeholder="e.g. Which shell companies is the CEO connected to?")

if st.button("Run Audit Trace", type="primary"):
    if not query:
        st.warning("Please enter a query.")
    else:
        with st.spinner("Initiating LangGraph Audit Workflow..."):
            
            # Start the graph execution
            state_input = {"question": query, "retries": 0, "reasoning_trace": []}
            
            try:
                # We use .invoke which runs the graph synchronously to completion
                final_state = audit_graph.invoke(state_input)
                
                # Display Results
                st.subheader("✅ Final Audit Answer")
                st.info(final_state.get("final_answer", "No answer generated."))
                
                st.divider()
                
                # Display Reasoning Trace
                st.subheader("🧠 Multi-Agent Reasoning Trace")
                trace = final_state.get("reasoning_trace", [])
                
                for step in trace:
                    with st.expander(f"Agent: {step.get('agent')} | Action: {step.get('action')}"):
                        st.json(step)
                        
            except Exception as e:
                st.error(f"Graph Execution Failed: {str(e)}. (Did you set Gemini API Keys and start Neo4j?)")
