import streamlit as st
import time

st.set_page_config(page_title="Sentinel-Graph Enterprise Auditor (Demo)", layout="wide")

st.title("🛡️ Sentinel-Graph Agentic Auditor (Demo Mode)")
st.markdown("Navigate complex enterprise graphs using Agentic Multi-Hop reasoning and Self-RAG.")

# Sidebar for Knowledge Injection
with st.sidebar:
    st.header("🧠 The Cartographer")
    st.markdown("Inject new documents into Neo4j via Specialist A.")
    new_doc = st.text_area("Audit Document / Knowledge:", height=150, value="On January 15, 2024, John Doe, CEO of Alpha Corp, signed a shadow contract named 'Project X' valued at $5,000,000 USD with a shell company called Beta Ltd.")
    if st.button("Process & Map Entities"):
        with st.spinner("Extracting Entities and Mapping to Graph..."):
            time.sleep(2)  # Simulate processing
            st.success(f"Extracted 4 Entities and 3 Relationships!")
            st.json({
                "entities": [
                    {"name": "John Doe", "type": "Person"},
                    {"name": "Alpha Corp", "type": "Company"},
                    {"name": "Project X", "type": "Contract"},
                    {"name": "Beta Ltd", "type": "Company"}
                ],
                "relationships": [
                    {"source": "John Doe", "target": "Alpha Corp", "relation_type": "CEO_OF"},
                    {"source": "John Doe", "target": "Project X", "relation_type": "SIGNED"},
                    {"source": "Project X", "target": "Beta Ltd", "relation_type": "INVOLVES"}
                ]
            })

# Main Query Section
st.header("🔍 The Detective & Auditor")
query = st.text_input("Enter Audit Question:", value="Which shell companies is the CEO of Alpha Corp connected to?")

if st.button("Run Audit Trace", type="primary"):
    if not query:
        st.warning("Please enter a query.")
    else:
        with st.spinner("Initiating LangGraph Audit Workflow..."):
            time.sleep(3) # Simulate graph traversal
            
            # Simulated Results
            st.subheader("✅ Final Audit Answer")
            st.info("Based on the audit, the findings are: John Doe, the CEO of Alpha Corp, is indirectly connected to the shell company 'Beta Ltd' through the signing of the $5,000,000 'Project X' shadow contract.")
            
            st.divider()
            
            # Simulated Reasoning Trace
            st.subheader("🧠 Multi-Agent Reasoning Trace")
            
            trace = [
                {
                    "agent": "Detective",
                    "action": "Generated Cypher",
                    "query": "MATCH (p:Person {name: 'John Doe'})-[:SIGNED]->(c:Contract)-[:INVOLVES]->(s:Company) RETURN s.name",
                    "reasoning": "Performing a multi-hop traversal from the Person to the Contract to find the hidden connected Shell Company."
                },
                {
                    "agent": "System",
                    "action": "Database Execution",
                    "results": "[{'s.name': 'Beta Ltd'}]"
                },
                {
                    "agent": "Auditor",
                    "action": "Evaluated Retrieval",
                    "score": 0.95,
                    "reasoning": "The Cypher query successfully traversed the graph to find the hidden shell company 'Beta Ltd' connected via 'Project X'. The results perfectly answer the audit question."
                },
                {
                    "agent": "System",
                    "action": "Final Output Generation",
                    "answer": "Based on the audit, the findings are: John Doe, the CEO of Alpha Corp, is indirectly connected to the shell company 'Beta Ltd' through the signing of the $5,000,000 'Project X' shadow contract."
                }
            ]
            
            for step in trace:
                with st.expander(f"Agent: {step.get('agent')} | Action: {step.get('action')}"):
                    st.json(step)
