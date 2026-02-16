# Contract Clause Intelligence Agent

An AI-powered RAG (Retrieval-Augmented Generation) system for analyzing federal contract clauses, FAR/DFARS provisions, and compliance requirements. Built as Portfolio Project #1 for the Enterprise AI Architect learning path.

> **All data is synthetic** - generated for portfolio demonstration purposes only.

## What It Does

Contract analysts and legal teams in defense contracting organizations spend days manually reviewing federal contracts to identify FAR/DFARS clauses, verify compliance requirements, and track flowdown obligations. This agent automates that analysis through natural language queries.

**Example queries:**
- "What are the mandatory flowdown clauses for subcontractors?"
- "Which contracts have CMMC certification requirements?"
- "Show me the DFARS 252.204-7012 cybersecurity obligations"
- "What are the termination clauses in firm-fixed-price contracts?"

## Architecture

```
                    +-------------------+
                    |   Streamlit UI    |
                    |  (Chat Interface) |
                    +--------+----------+
                             |
                    +--------v----------+
                    |  Contract Agent   |
                    |  (Query Router)   |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+         +---------v---------+
    |    Retriever       |         |    LLM Backend    |
    | (ChromaDB + MMR)  |         | (Mock or Claude)  |
    +---------+----------+         +-------------------+
              |
    +---------v----------+
    |   Vector Store     |
    |   (ChromaDB)       |
    |   ~3000+ chunks    |
    +--------------------+
              ^
              |  Embedding (sentence-transformers)
              |
    +---------+----------+
    | Clause-Aware       |
    | Document Chunker   |
    +--------------------+
              ^
              |
    +---------+----------+
    | 120 Synthetic      |
    | Federal Contracts  |
    +--------------------+
```

**Key architectural decisions:**
- **Clause-aware chunking**: Unlike generic text splitters, our chunker understands federal contract structure and splits on section boundaries (FAR clauses, CLINs, SOW, etc.)
- **Local embeddings**: Uses `sentence-transformers/all-MiniLM-L6-v2` - no API key needed for embeddings
- **Dual LLM mode**: Mock mode for testing (no API cost), Claude mode for production quality
- **Rich metadata**: Every chunk carries contract number, clause number, section type, and flowdown status

## Quick Start

### Prerequisites
- Python 3.10+
- 4GB free disk space (for embeddings model + vector store)

### Setup

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/contract-intelligence-agent.git
cd contract-intelligence-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (generates data + builds vector store)
python run_pipeline.py

# Launch the Streamlit app
streamlit run app/streamlit_app.py
```

### Using Claude (Optional)

```bash
# Copy environment template
cp .env.example .env

# Edit .env and set your API key
# ANTHROPIC_API_KEY=sk-ant-...
# LLM_MODE=anthropic
```

Then select "anthropic" mode in the Streamlit sidebar.

## Project Structure

```
contract-intelligence-agent/
├── app/
│   └── streamlit_app.py          # Streamlit chat interface
├── config/
│   └── settings.py               # Pydantic settings from .env
├── data/
│   ├── synthetic/                # Generated contract data
│   │   ├── documents/            # Text files for RAG ingestion
│   │   └── _corpus.json          # Full structured corpus
│   └── processed/
│       └── chroma_db/            # Persisted vector store
├── src/
│   ├── data_generation/
│   │   ├── far_clauses.py        # FAR/DFARS clause reference data
│   │   └── contract_generator.py # Synthetic contract generator
│   ├── ingestion/
│   │   ├── chunker.py            # Clause-aware document chunker
│   │   └── document_loader.py    # Document loading pipeline
│   ├── retrieval/
│   │   └── vector_store.py       # ChromaDB setup and retrieval
│   └── agent/
│       ├── prompts.py            # System and RAG prompts
│       ├── mock_llm.py           # Mock LLM for testing
│       └── contract_agent.py     # Main RAG agent
├── tests/
├── run_pipeline.py               # One-command setup script
├── requirements.txt
├── .env.example
└── README.md
```

## Synthetic Data

The generator creates 120 federal contracts with realistic attributes:

| Contract Type | Count | Description |
|--------------|-------|-------------|
| FFP | 35 | Firm-Fixed-Price |
| CPFF | 20 | Cost-Plus-Fixed-Fee |
| CPAF | 10 | Cost-Plus-Award-Fee |
| T&M | 15 | Time-and-Materials |
| LH | 10 | Labor-Hour |
| IDIQ | 15 | Indefinite Delivery/Indefinite Quantity |
| BPA | 10 | Blanket Purchase Agreement |
| Task Orders | 5+ | Under IDIQ vehicles |

Each contract includes: contract number, agency, contractor info, CAGE codes, CLINs, period of performance, FAR clauses, DFARS clauses, subcontractor requirements, security requirements, and special provisions.

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| LLM | Claude (Anthropic) or Mock | Response generation |
| Embeddings | sentence-transformers | Local document vectorization |
| Vector Store | ChromaDB | Similarity search |
| Framework | LangChain | RAG pipeline orchestration |
| Frontend | Streamlit | Interactive chat UI |
| Data Gen | Python + Faker | Synthetic contract generation |

## Skills Demonstrated

- **RAG Pipeline Architecture**: End-to-end retrieval-augmented generation
- **Domain-Specific Chunking**: Custom chunker for federal contract structure
- **Vector Search**: ChromaDB with metadata filtering
- **Prompt Engineering**: System prompts for contract analysis accuracy
- **Full-Stack AI Application**: Backend agent + interactive frontend
- **Synthetic Data Generation**: Realistic federal contract simulation
- **Defense Contracting Domain Knowledge**: FAR/DFARS, CMMC, NIST SP 800-171

## License

MIT License - See [LICENSE](LICENSE) for details.

---

*Part of the Enterprise AI Architect Portfolio - Project 1 of 5*
