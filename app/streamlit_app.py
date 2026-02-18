"""Contract Clause Intelligence Agent - Streamlit Frontend.

Interactive web application for querying synthetic federal contracts
using RAG (Retrieval-Augmented Generation).

Run with: streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

import streamlit as st

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent.contract_agent import ContractAgent
from src.ingestion.document_loader import get_corpus_stats


# --- Page Configuration ---
st.set_page_config(
    page_title="Contract Clause Intelligence Agent",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Custom CSS ---
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: 700;
        color: #1B2A4A;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #636E72;
        margin-bottom: 2rem;
    }
    .source-card {
        background-color: #f8f9fa;
        border-left: 4px solid #0D7377;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        border-radius: 0 4px 4px 0;
    }
    .badge {
        display: inline-block;
        padding: 0.15rem 0.5rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 0.3rem;
    }
    .badge-far { background-color: #E3F2FD; color: #1565C0; }
    .badge-dfars { background-color: #FFF3E0; color: #E65100; }
    .badge-clin { background-color: #E8F5E9; color: #2E7D32; }
    .badge-sow { background-color: #F3E5F5; color: #6A1B9A; }
    .synthetic-banner {
        background-color: #FFF8E1;
        border: 1px solid #FFE082;
        padding: 0.5rem 1rem;
        border-radius: 4px;
        font-size: 0.85rem;
        color: #F57F17;
        text-align: center;
        margin-bottom: 1rem;
    }
    .stat-box {
        text-align: center;
        padding: 1rem;
        background-color: #f0f4f8;
        border-radius: 8px;
    }
    .stat-number {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0D7377;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #636E72;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "uploaded_count" not in st.session_state:
    st.session_state.uploaded_count = 0
if "last_upload_result" not in st.session_state:
    st.session_state.last_upload_result = None


def get_badge_class(chunk_type: str) -> str:
    """Get CSS class for source badge."""
    if chunk_type == "clause":
        return "badge-far"
    elif chunk_type == "clin":
        return "badge-clin"
    elif chunk_type == "scope_of_work":
        return "badge-sow"
    return "badge-dfars"


def initialize_agent():
    """Initialize the contract agent."""
    mode = st.session_state.get("llm_mode", "mock")
    api_key = st.session_state.get("api_key", "")

    try:
        agent = ContractAgent(
            mode=mode,
            persist_directory="./data/processed/chroma_db",
            anthropic_api_key=api_key if mode == "anthropic" else None,
        )
        st.session_state.agent = agent
        return True
    except FileNotFoundError as e:
        st.error(f"Vector store not found. Please run the setup pipeline first:\n\n```\npython run_pipeline.py\n```")
        return False
    except Exception as e:
        st.error(f"Failed to initialize agent: {e}")
        return False


# --- Sidebar ---
with st.sidebar:
    st.markdown("### Configuration")

    st.markdown('<div class="synthetic-banner">All data is synthetic - for demonstration only</div>', unsafe_allow_html=True)

    # Mode selection
    mode = st.radio(
        "LLM Mode",
        options=["mock", "anthropic"],
        index=0,
        help="Mock mode works without API keys. Anthropic mode uses Claude for higher quality responses.",
    )
    st.session_state.llm_mode = mode

    if mode == "anthropic":
        api_key = st.text_input("Anthropic API Key", type="password", key="api_key_input")
        st.session_state.api_key = api_key

    # Initialize button
    if st.button("Initialize Agent", type="primary", use_container_width=True):
        with st.spinner("Loading vector store and initializing agent..."):
            if initialize_agent():
                st.success("Agent ready!")
            else:
                st.error("Initialization failed.")

    st.markdown("---")

    # Corpus stats
    st.markdown("### Corpus Statistics")
    try:
        stats = get_corpus_stats("./data/synthetic")
        if "error" not in stats:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Contracts", stats["total_contracts"])
                st.metric("DoD", stats["dod_contracts"])
            with col2:
                st.metric("Value", f"${stats['total_value']/1e9:.1f}B")
                st.metric("Civilian", stats["civilian_contracts"])
        else:
            st.info("Generate contracts first with:\n`python run_pipeline.py`")
    except Exception:
        st.info("No corpus data found yet.")

    # Agent stats
    if st.session_state.agent:
        st.markdown("---")
        st.markdown("### Agent Status")
        agent_stats = st.session_state.agent.get_stats()
        st.metric("Vectors Indexed", agent_stats["total_vectors"])
        st.caption(f"Mode: {agent_stats['mode']} | Top-K: {agent_stats['top_k']}")

    # --- Document Upload Section ---
    if st.session_state.agent:
        st.markdown("---")
        st.markdown("### Upload Contract")
        st.caption("Add a new contract to the corpus in real time.")

        uploaded_file = st.file_uploader(
            "Choose a contract file (.txt or .docx)",
            type=["txt", "docx"],
            help=(
                "Upload a contract document. "
                "**.txt** files must follow the standard format with CONTRACT NUMBER and section headers. "
                "**.docx** files are processed via hybrid extraction (regex + LLM) to automatically "
                "extract structured fields, clauses, and narrative content."
            ),
            key="contract_uploader",
        )

        if uploaded_file is not None:
            is_docx = uploaded_file.name.lower().endswith(".docx")

            if st.button("Process & Index", type="primary", use_container_width=True):
                if is_docx:
                    _process_docx_upload(uploaded_file)
                else:
                    _process_txt_upload(uploaded_file)

        # Show upload history
        if st.session_state.uploaded_count > 0:
            st.success(
                f"{st.session_state.uploaded_count} document(s) uploaded this session"
            )

    st.markdown("---")

    # Sample queries
    st.markdown("### Sample Questions")
    sample_queries = [
        "What are the mandatory flowdown clauses for subcontractors?",
        "Which contracts have CMMC certification requirements?",
        "Show me cybersecurity requirements across IDIQ contracts",
        "What are the DFARS 252.204-7012 obligations?",
        "List contracts with subcontractor provisions over $1M",
        "What are the termination clauses in FFP contracts?",
        "Explain the Equal Opportunity requirements",
        "Which contracts require NIST SP 800-171 compliance?",
    ]
    for q in sample_queries:
        if st.button(q, key=f"sample_{hash(q)}", use_container_width=True):
            st.session_state.pending_query = q


def _process_txt_upload(uploaded_file):
    """Handle .txt file upload processing."""
    file_content = uploaded_file.read().decode("utf-8")

    with st.status("Ingesting document into corpus...", expanded=True) as status:
        st.write("Validating document format...")
        from src.ingestion.upload_manager import validate_upload
        is_valid, error_msg = validate_upload(file_content, uploaded_file.name)

        if not is_valid:
            st.error(f"Validation failed: {error_msg}")
            status.update(label="Upload failed", state="error")
        else:
            st.write("Document structure verified.")
            st.write("Splitting into clause-aware chunks...")

            result = st.session_state.agent.ingest_document(
                file_content=file_content,
                filename=uploaded_file.name,
            )

            if result.get("error"):
                st.error(f"Processing error: {result['error']}")
                status.update(label="Upload failed", state="error")
            else:
                st.write(
                    f"Created **{result['num_chunks']}** chunks "
                    f"from contract **{result['contract_number']}**"
                )
                type_parts = [
                    f"{count} {ctype}"
                    for ctype, count in result["chunk_types"].items()
                ]
                st.write(f"Chunk types: {', '.join(type_parts)}")
                st.write(
                    f"**{result['new_total_vectors']}** total vectors now indexed."
                )
                status.update(label="Document indexed successfully!", state="complete")
                st.session_state.uploaded_count += 1
                st.session_state.last_upload_result = result


def _process_docx_upload(uploaded_file):
    """Handle .docx file upload with hybrid extraction progress display."""
    file_bytes = uploaded_file.read()

    with st.status("Extracting and indexing Word document...", expanded=True) as status:
        st.write("Parsing Word document...")
        st.write("Extracting structured fields (regex)...")
        st.write("Extracting narrative fields (LLM)...")
        st.write("Merging results and generating contract record...")

        result = st.session_state.agent.ingest_document(
            file_content=file_bytes,
            filename=uploaded_file.name,
        )

        if not result.get("valid"):
            st.error(f"Processing error: {result.get('error', 'Unknown error')}")
            status.update(label="Upload failed", state="error")
        else:
            st.write("Chunking and indexing into vector store...")
            st.write(
                f"Created **{result['num_chunks']}** chunks "
                f"from contract **{result['contract_number']}**"
            )
            type_parts = [
                f"{count} {ctype}"
                for ctype, count in result.get("chunk_types", {}).items()
            ]
            if type_parts:
                st.write(f"Chunk types: {', '.join(type_parts)}")
            st.write(
                f"**{result['new_total_vectors']}** total vectors now indexed."
            )

            status.update(label="Word document extracted and indexed!", state="complete")
            st.session_state.uploaded_count += 1
            st.session_state.last_upload_result = result

            # Show extraction report in expander
            report = result.get("extraction_report")
            if report:
                with st.expander("Extraction Report", expanded=True):
                    cols = st.columns(4)
                    cols[0].metric("Total Fields", report["total_fields"])
                    cols[1].metric("Regex Extracted", report["regex_extracted"])
                    cols[2].metric("LLM Extracted", report["llm_extracted"])
                    cols[3].metric("Avg Confidence", f"{report['confidence_avg']:.0%}")

                    if report.get("warnings"):
                        st.markdown("**Warnings:**")
                        for warning in report["warnings"]:
                            st.caption(f"- {warning}")


# --- Main Content ---
st.markdown('<div class="main-header">Contract Clause Intelligence Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">AI-powered analysis of federal contract clauses, '
    'FAR/DFARS provisions, and compliance requirements</div>',
    unsafe_allow_html=True,
)

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("sources"):
            with st.expander(f"View {len(msg['sources'])} source(s)", expanded=False):
                for src in msg["sources"]:
                    badge_class = get_badge_class(src.get("chunk_type", ""))
                    clause_info = f" | {src['clause_number']}" if src.get("clause_number") else ""
                    st.markdown(
                        f'<div class="source-card">'
                        f'<span class="badge {badge_class}">{src.get("chunk_type", "general").upper()}</span> '
                        f'<strong>{src["contract_number"]}{clause_info}</strong>'
                        f'<br><small>{src.get("preview", "")[:120]}...</small>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

# Handle pending query from sample buttons
if "pending_query" in st.session_state:
    query = st.session_state.pop("pending_query")
    st.session_state.messages.append({"role": "user", "content": query})
    st.rerun()

# Chat input
if prompt := st.chat_input("Ask about contract clauses, compliance requirements, or FAR/DFARS provisions..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Process the latest user message if agent is ready
if (
    st.session_state.messages
    and st.session_state.messages[-1]["role"] == "user"
    and st.session_state.agent
    and (
        len(st.session_state.messages) < 2
        or st.session_state.messages[-2]["role"] != "assistant"
        or st.session_state.messages[-2]["content"] != st.session_state.messages[-1]["content"]
    )
):
    last_user_msg = st.session_state.messages[-1]["content"]

    # Check if we already have a response for this message
    if len(st.session_state.messages) < 2 or st.session_state.messages[-1]["role"] == "user":
        with st.chat_message("assistant"):
            with st.spinner("Searching contract corpus and analyzing..."):
                result = st.session_state.agent.query(last_user_msg)

            st.markdown(result["answer"])

            if result["sources"]:
                with st.expander(f"View {len(result['sources'])} source(s)", expanded=False):
                    for src in result["sources"]:
                        badge_class = get_badge_class(src.get("chunk_type", ""))
                        clause_info = f" | {src['clause_number']}" if src.get("clause_number") else ""
                        st.markdown(
                            f'<div class="source-card">'
                            f'<span class="badge {badge_class}">{src.get("chunk_type", "general").upper()}</span> '
                            f'<strong>{src["contract_number"]}{clause_info}</strong>'
                            f'<br><small>{src.get("preview", "")[:120]}...</small>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "sources": result["sources"],
        })

# Show welcome message if no conversation yet
if not st.session_state.messages:
    if not st.session_state.agent:
        st.info(
            "Click **Initialize Agent** in the sidebar to get started. "
            "Make sure you've run the setup pipeline first (`python run_pipeline.py`)."
        )
    else:
        st.markdown(
            "Ready to analyze contracts! Try one of the sample questions in the sidebar, "
            "or type your own question below."
        )
