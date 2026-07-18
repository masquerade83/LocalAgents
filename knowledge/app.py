"""Streamlit UI for GraphRAG whitepaper knowledge system."""

from __future__ import annotations

import streamlit as st

from config import OLLAMA_CHAT_MODEL, WHITEPAPERS_PATH
from graph_query import GraphQuery
from grounded_answer import answer_question
from hybrid_retriever import retrieve
from vector_query import chunk_count, search


st.set_page_config(page_title="Whitepaper GraphRAG", page_icon="🧠", layout="wide")
st.title("Whitepaper GraphRAG")
st.caption(f"Neo4j knowledge graph + Chroma semantic search · Ollama `{OLLAMA_CHAT_MODEL}`")


@st.cache_resource
def graph_query():
    return GraphQuery()


def overview_tab() -> None:
    gq = graph_query()
    stats = gq.stats()
    chunks = chunk_count()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Papers", stats.get("papers", 0))
    c2.metric("Concepts", stats.get("concepts", 0))
    c3.metric("Citations", stats.get("citations", 0))
    c4.metric("Vector chunks", chunks)

    st.subheader("Ingested papers")
    for paper in gq.list_papers():
        st.write(f"- **{paper['title']}** (`{paper['id']}`)" + (f" — {paper['year']}" if paper.get("year") else ""))

    st.subheader("Cross-paper concept bridges")
    bridges = gq.concept_bridge(limit=10)
    if bridges:
        st.dataframe(bridges, use_container_width=True)
    else:
        st.info("No concept bridges found.")


def graph_explorer_tab() -> None:
    gq = graph_query()
    keyword = st.text_input("Search concept keyword", placeholder="e.g. O-RAN, LLM, 5G")
    if keyword:
        concepts = gq.search_concepts(keyword, limit=10)
        st.write("Matching concepts:", concepts or "None")
        for concept in concepts[:5]:
            papers = gq.papers_for_concept(concept)
            st.markdown(f"**{concept}**")
            for p in papers:
                st.write(f"  - {p['title']}")


def semantic_search_tab() -> None:
    query = st.text_input("Semantic search", placeholder="network slicing in 5G RAN")
    paper_filter = st.text_input("Optional paper_id filter", placeholder="telcogpt")
    top_k = st.slider("Top K", 3, 15, 8)

    if st.button("Search", type="primary") and query:
        paper_ids = [paper_filter.strip()] if paper_filter.strip() else None
        hits = search(query, top_k=top_k, paper_ids=paper_ids)
        if not hits:
            st.warning("No results. Run vector ingest: `python ingest_all.py --vectors-only`")
            return
        for i, hit in enumerate(hits, 1):
            with st.expander(f"[{i}] {hit['paper_title']} — {hit['section_title']} (dist={hit['distance']:.3f})"):
                st.write(hit["text"])


def ask_tab() -> None:
    question = st.text_area(
        "Ask a question",
        placeholder="How does TelcoGPT approach domain-specific language for telecom?",
        height=100,
    )
    use_graph = st.checkbox("Use graph pre-filter", value=True)
    paper_filter = st.text_input("Limit to paper_id (optional)", key="ask_paper")

    if st.button("Ask", type="primary") and question:
        with st.spinner("Retrieving and generating answer..."):
            paper_ids = [paper_filter.strip()] if paper_filter.strip() else None
            result = answer_question(question, paper_ids=paper_ids, use_graph_filter=use_graph)

        st.subheader("Answer")
        st.markdown(result["answer"])

        retrieval = result["retrieval"]
        if retrieval.get("matched_concepts"):
            st.caption(f"Graph concepts: {', '.join(retrieval['matched_concepts'])}")
        if retrieval.get("paper_filter"):
            st.caption(f"Paper filter: {', '.join(retrieval['paper_filter'])}")

        st.subheader("Source passages")
        for i, p in enumerate(retrieval.get("passages") or [], 1):
            with st.expander(f"[{i}] {p.get('paper_title')} — {p.get('section_title')}"):
                st.write(p.get("text", ""))


tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Graph Explorer", "Semantic Search", "Ask (GraphRAG)"])
with tab1:
    overview_tab()
with tab2:
    graph_explorer_tab()
with tab3:
    semantic_search_tab()
with tab4:
    ask_tab()

st.sidebar.markdown("### Corpus")
st.sidebar.code(str(WHITEPAPERS_PATH))
st.sidebar.markdown("### Commands")
st.sidebar.code("python ingest_all.py --vectors-only\nstreamlit run app.py")
