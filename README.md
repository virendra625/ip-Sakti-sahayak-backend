# IP-SAKTI Sahayak — Backend

**A Multilingual, RAG-Based, Source-Cited AI Assistant for Intellectual Property Rights (IPR) and Regulatory Guidance Related to Ayurveda.**

Built for the **Smart India Hackathon (SIH)**.

---

## 1. Project Overview

**IP-SAKTI Sahayak** is a production-structured decision-support system designed to empower Ayurvedic innovators, researchers, startups, and MSMEs to navigate the complex intersection of Indian Intellectual Property Rights (IPR) and statutory drug regulations.

### Core Objectives
1. **Product Classification**: Analyzes formulations into statutory categories under Chapter IV-A of the Drugs and Cosmetics Act, 1940 (Classical ASU vs. Patent/Proprietary vs. Phytopharmaceutical vs. FSSAI Ayurveda Aahar).
2. **Strict Jurisdiction Isolation**: Guarantees that Indian laws (Patents Act 1970 § 3(p), Biological Diversity Act 2002) are never silently mixed with foreign or international treaties.
3. **Source Grounding & Citations**: Every claim made by the assistant is grounded in authoritative statutory chunks and linked to authentic source citations (`[1] Title, Authority, Section, Page, Version`).
4. **Anti-Hallucination Guardrails**: If no authoritative evidence exists in the knowledge base, the system refuses to guess and explicitly informs the user.
5. **Multilingual Decision Support**: Natively supports queries in English and Hindi (with Devanagari script detection) while preserving original English statutory citations without alteration.
6. **Zero-Cost Local Execution**: Features local SQLite and embedded Qdrant fallback with a deterministic mock LLM & embedding provider, allowing student developers to run the entire backend offline without requiring paid API keys or Docker!

> [!NOTE]
> **Legal Disclaimer**:
> This system is an informational decision-support tool, NOT a replacement for a patent attorney, Ayurvedic doctor, regulatory consultant, or the State Licensing Authority (AYUSH).

---

---

## 2. System Architecture & End-to-End Information Flow

The backend follows a strictly grounded, deterministic retrieval-augmented generation (RAG) pipeline to prevent hallucination of statutory provisions:

### The Complete Flow
```
Frontend (React / Vite)
        │
        ▼  [1. POST /api/v1/chat with query, language, jurisdiction, product context]
FastAPI Backend Gateway (Input sanitization, session management, CORS)
        │
        ▼  [2. Query translation & domain term enrichment]
RAG Service (TranslationService, normalize_jurisdiction, classification hook)
        │
        ▼  [3. Hybrid vector similarity query with strict jurisdiction & topic filters]
Qdrant Vector Database (Vector embeddings + statutory payload metadata)
        │
        ▼  [4. Exact statute sections retrieved: Section 3(p), Section 2(1)(zb), etc.]
Retrieved Government-Source Evidence (Curated statutory excerpts from official documents)
        │
        ▼  [5. Grounded prompt assembly with retrieved chunks]
LLM Engine (Mock deterministic offline provider / Gemini 1.5 Flash / OpenAI GPT-4o-mini)
        │
        ▼  [6. Raw answer text with bracketed citations e.g. [Source 1]]
URL Validation & Sanitization (URLService verifies official government domains)
        │
        ▼  [7. Claim-level verification: checks enclosing claim against source domain]
Citation Auditor (CitationService & EvidenceService: ensures only supporting sources returned)
        │
        ▼  [8. Grounded answer + verified official URLs + confidence score + disclaimer]
Final Answer Delivered to Frontend
```

### Beginner's Guide: What Each Component Does in Simple Words

- **Mock LLM vs. Gemini / OpenAI**:
  - *Mock LLM Provider (Default)*: An intelligent, deterministic, zero-cost reasoning engine built into the backend. It reads retrieved statutory chunks and synthesizes question-specific legal guidance without needing any API key, internet connection, or external cloud. Perfect for offline hackathon demos, local development, and CI tests.
  - *Gemini & OpenAI Providers (Production)*: When you provide an API key in `.env` (`LLM_PROVIDER=gemini` or `openai`), the backend switches to state-of-the-art foundation models. Even then, the models are constrained by strict system prompts to answer *only* using the retrieved government evidence.
- **Qdrant Vector Database**:
  - Acts as a semantic search engine. Unlike simple keyword search that looks for exact words, Qdrant understands mathematical meaning. If a user asks *"How do I protect my brand name?"*, Qdrant matches it with statutory chunks from the *Trade Marks Act, 1999* even if the user never typed the word "trademark". It also enforces strict filters so Indian laws are never mixed with foreign jurisdictions.
- **RAG (Retrieval-Augmented Generation)**:
  - Standard AI models often "hallucinate" (invent fake laws, incorrect sections, or non-existent court rulings). RAG stops this by forcing the AI into an "open-book exam": first, the system retrieves the exact authentic legal text from government statutes; then, the AI reads those retrieved chunks and answers the user's question based strictly on that evidence.
- **Citations & Claim-Level Validation**:
  - Every legal claim made in the answer is tagged with a citation bracket like `[Source 1]`. Our `CitationService` inspects the text surrounding each bracket to verify that the specific claim matches the topic of the cited source (for example, a trademark sentence cannot cite the Patents Act). Chunks that were retrieved but not actually used to support any statement are discarded from the final response.
- **Official URL Validation (`URLService`)**:
  - Ensures every source link presented to the user belongs to an authentic, active government portal (IPO, CGPDTM, NBA, FSSAI, CDSCO). Any hallucinated, unverified, or broken URLs are automatically stripped before reaching the user.
- **Why This Is Legal Informational Guidance and Not Legal Advice**:
  - Statutory classification and patentability depend on subjective legal analysis and official examination by government bodies (such as the Indian Patent Office, National Biodiversity Authority, or AYUSH State Licensing Authorities). IP-SAKTI Sahayak provides preliminary decision-support to help innovators prepare compliant applications, but does not replace licensed legal practitioners.

---

## 3. Technology Stack

- **Framework**: Python 3.11+ / FastAPI
- **Data Validation**: Pydantic v2 & Pydantic-Settings
- **ORM & Database**: SQLAlchemy 2.0 with PostgreSQL (Production) and SQLite (Offline Local Fallback)
- **Vector Database**: Qdrant (Docker, Cloud, or Local Embedded storage)
- **Document Processing**: PyPDF / PyMuPDF (fitz) with structural section detection
- **Testing**: Pytest & FastAPI TestClient
- **LLM / Embeddings**: Configurable abstract service supporting Google Gemini, OpenAI, and Local/Mock offline providers

---

## 4. Project Directory Structure

```
ip-sakti-sahayak-backend/
├── app/
│   ├── main.py                          # FastAPI app factory, CORS, exception handlers, and routing
│   ├── core/
│   │   ├── config.py                    # Environment settings, CORS, and provider configs
│   │   ├── logging.py                   # Structured logging with Request-ID tracking & key masking
│   │   └── security.py                  # Input sanitization and future JWT authentication hooks
│   ├── db/
│   │   ├── database.py                  # SQLAlchemy engine, session maker, and init_db()
│   │   └── session.py                   # Session dependency injection alias
│   ├── models/
│   │   ├── document.py                  # Document metadata model (statute, authority, version)
│   │   ├── document_chunk.py            # Granular text chunk model with page & section
│   │   ├── product.py                   # Ayurvedic formulation model
│   │   ├── conversation.py              # Dialogue session model
│   │   ├── message.py                   # User/Assistant chat messages
│   │   ├── citation.py                  # Citation mapping model linking messages to chunks
│   │   └── feedback.py                  # Evaluation feedback model (helpful, wrong citation, etc.)
│   ├── schemas/
│   │   ├── common.py                    # Standard response envelopes and error models
│   │   ├── chat.py                      # ChatRequest, ChatResponse, CitationDetail, ConfidenceDetail
│   │   ├── classification.py            # ProductClassificationRequest, ProductClassificationResponse
│   │   ├── document.py                  # DocumentCreate, DocumentResponse, Ingestion payloads
│   │   ├── source.py                    # SourceItem, SearchRequest, SearchResponse
│   │   └── feedback.py                  # FeedbackCreate, FeedbackResponse
│   ├── services/
│   │   ├── llm_service.py               # Abstract LLM provider (Mock, Gemini, OpenAI)
│   │   ├── embedding_service.py         # Abstract embedding provider (Mock 384-dim, OpenAI)
│   │   ├── rag_service.py               # End-to-end RAG orchestrator pipeline
│   │   ├── classification_service.py    # Ayurvedic regulatory & IPR classifier
│   │   ├── citation_service.py          # Citation extraction, parsing, and formatting
│   │   ├── evidence_service.py          # Evidence strength scoring & conflict detector
│   │   ├── translation_service.py       # English/Hindi cross-lingual query expander
│   │   ├── graph_interface.py          # Node/Edge interfaces for future Neo4j Knowledge Graph
│   │   └── agent_interfaces.py         # Multi-agent scaffolding for future autonomous expansion
│   ├── repositories/
│   │   ├── document_repository.py       # CRUD & filtering for documents and chunks
│   │   ├── conversation_repository.py   # Multi-turn conversation and citation persistence
│   │   └── product_repository.py        # Product formulation persistence
│   ├── rag/
│   │   ├── ingestion.py                 # Text and PDF dual-ingestion pipeline (DB + Qdrant)
│   │   ├── chunking.py                  # Section-aware, page-aware structural text chunker
│   │   ├── metadata.py                  # Taxonomy for IPR, AYUSH, and regulatory domains
│   │   ├── retriever.py                 # Hybrid Qdrant retriever with jurisdiction filters
│   │   └── prompt_templates.py          # Anti-hallucination system prompts in English & Hindi
│   ├── utils/
│   │   ├── text_cleaner.py              # Text sanitization and legal header extraction
│   │   ├── language.py                  # Devanagari / English language detection
│   │   └── validators.py                # Jurisdiction and topic validators
│   └── api/
│       └── routes/
│           ├── health.py                # GET /api/v1/health (Liveness and component check)
│           ├── chat.py                  # POST /api/v1/chat (Core conversational RAG assistant)
│           ├── classification.py        # POST /api/v1/classification (Product formulation classifier)
│           ├── documents.py             # Ingestion & listing endpoints for legal documents
│           ├── sources.py               # GET /api/v1/sources (Authoritative indexed sources)
│           ├── jurisdictions.py         # GET /api/v1/jurisdictions (Supported legal regions)
│           ├── topics.py                # GET /api/v1/topics (Taxonomic list of topics)
│           ├── search.py                # POST /api/v1/search (Direct retrieval debug endpoint)
│           └── feedback.py              # POST /api/v1/feedback (User evaluation logging)
├── data/
│   └── documents/                       # Authoritative & sample legal documents
├── scripts/
│   ├── ingest_documents.py              # CLI tool to chunk & index documents into DB & Qdrant
│   └── create_sample_data.py            # CLI tool to seed sample formulations and verify state
├── tests/                               # 19 comprehensive pytest tests
├── requirements.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 5. Quickstart Guide (Local Setup in 5 Minutes)

### Prerequisites
- Python 3.11+ installed (`python --version`)
- Git

### Step 1: Clone or Navigate to Project
```bash
cd C:\Users\hp\.gemini\antigravity\scratch\ip-sakti-sahayak-backend
```

### Step 2: Create and Activate Virtual Environment
```bash
python -m venv venv
# On Windows PowerShell:
.\venv\Scripts\Activate.ps1
# On Linux / macOS:
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(By default, `.env` uses SQLite and local embedded Qdrant with the Mock LLM. You do NOT need any API keys or Docker to get started!)*

### Step 5: Seed Sample Documents & Formulations
Run the ingestion and sample seeding scripts:
```bash
python scripts/ingest_documents.py
python scripts/create_sample_data.py
```

### Step 6: Start the FastAPI Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open your browser to:
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc Documentation: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 6. Running with Docker (PostgreSQL & Qdrant)

If you prefer to run dedicated PostgreSQL and Qdrant instances using Docker:

### Option A: Using Docker Compose
```bash
docker-compose up -d
```
Update your `.env`:
```ini
DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/ipsakti
QDRANT_URL=http://localhost:6333
```
Then re-run:
```bash
python scripts/ingest_documents.py
```

### Option B: Zero-Docker Offline Mode
Leave `DATABASE_URL=sqlite:///./ip_sakti.db` and `QDRANT_URL=http://localhost:6333` in `.env`. When the backend notices that Docker is not running, it **automatically** falls back to local SQLite and embedded Qdrant storage.

---

## 7. Connecting Real AI Models (Gemini / OpenAI)

To switch from the default offline mock provider to real LLMs:

### For Google Gemini
1. Get an API key from Google AI Studio.
2. In `.env`:
   ```ini
   LLM_PROVIDER=gemini
   LLM_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-1.5-flash
   ```

### For OpenAI
1. In `.env`:
   ```ini
   LLM_PROVIDER=openai
   LLM_API_KEY=your_openai_api_key_here
   OPENAI_MODEL=gpt-4o-mini
   EMBEDDING_PROVIDER=openai
   EMBEDDING_API_KEY=your_openai_api_key_here
   ```

---

## 8. Detailed Walkthrough of Key Modules

### How a User Question Travels Through the Backend
1. **User Request**: The frontend sends a POST request to `/api/v1/chat` with `message`, `language`, `jurisdiction`, and optional `product_context`.
2. **Security & Sanitization**: `app/core/security.py` sanitizes the text, checks against script injection, and normalizes input length.
3. **Session & History**: `ConversationRepository` retrieves or creates a database dialogue session.
4. **Multilingual Processing**: If the query is in Hindi, `TranslationService` detects the Devanagari script and augments statutory search terms in English.
5. **Jurisdiction Isolation**: `app/utils/validators.py` ensures strict jurisdiction boundaries. If the user asks an open patent question without choosing a country, the engine asks: *"Which jurisdiction should I analyse?"*
6. **Vector Search (Qdrant)**: `QdrantRetriever` filters by jurisdiction and topic, then calculates cosine similarity against document chunks.
7. **Prompt Assembly**: `app/rag/prompt_templates.py` builds a guarded system prompt injecting the retrieved statutory sections.
8. **LLM Generation**: The configured LLM provider synthesizes an answer referencing bracketed citations (e.g. `[1]`, `[2]`).
9. **Evidence & Citation Audit**: `EvidenceService` verifies that every citation maps to a genuine chunk in the database, checks for legal conflicts, and assigns an evidence strength indicator (`HIGH`, `MEDIUM`, `LOW`, `INSUFFICIENT`).
10. **Storage & Return**: The assistant message and its citations are saved to PostgreSQL/SQLite, and the response is returned with mandatory legal disclaimers.

---

## 9. API Reference & Example Calls

### 1. Product Classification
**`POST /api/v1/classification`**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/classification" \
     -H "Content-Type: application/json" \
     -d '{
       "product_name": "Classical Chyawanprash",
       "product_description": "Polyherbal jam prepared strictly in accordance with Charaka Samhita formulas with Amla.",
       "is_classical_text_source": true,
       "has_formulation_been_modified": false,
       "intended_use": "Therapeutic rejuvenation and vitality",
       "jurisdiction": "India"
     }'
```

**Response**:
```json
{
  "likely_category": "Classical_ASU_Medicine",
  "confidence": 0.90,
  "reasoning_summary": "Manufactured strictly in accordance with formulae described in authoritative Ayurvedic texts (First Schedule of Drugs & Cosmetics Act, 1940, Section 3(a)).",
  "missing_information": [],
  "relevant_topics": ["AYUSH", "Classical_Medicine", "Licensing", "Traditional_Knowledge"],
  "ipr_implications": [
    "Strictly NON-PATENTABLE in India under Section 3(p) of the Patents Act, 1970 (Traditional Knowledge).",
    "Monopoly rights cannot be claimed over classical ASU names; protection relies on Trademark for brand identity."
  ],
  "disclaimer": "Likely classification based on provided information. This response is for informational and decision-support purposes only..."
}
```

---

### 2. Conversational RAG Turn
**`POST /api/v1/chat`**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "Can an Ayurvedic classical formulation be patented in India?",
       "jurisdiction": "India",
       "language": "en"
     }'
```

**Response**:
```json
{
  "conversation_id": "demo_session",
  "message_id": 1,
  "answer": "Based on the authoritative sources retrieved, under The Patents Act, 1970 - Section 3(p) & Biological Resources (Section 3(p)):\n\n• According to The Patents Act, 1970: Pure formulations of Ayurveda that represent traditional knowledge known to the public through classical texts cannot be granted patent monopoly under Section 3(p)... [1]\n\nAccordingly, any claims relating to Ayurvedic formulations must be evaluated against these specific statutory requirements.",
  "language": "en",
  "jurisdiction": "India",
  "confidence": {
    "level": "HIGH",
    "score": 0.85,
    "reason": "Strongly grounded in 5 authoritative source chunk(s) from India with high semantic and statutory alignment."
  },
  "citations": [
    {
      "citation_id": 1,
      "document_id": 1,
      "document_title": "The Patents Act, 1970 - Section 3(p) & Biological Resources",
      "authority": "Indian Patent Office (IPO) / Parliament of India",
      "section": "Section 3(p)",
      "page": "1",
      "version": "2005_amendment",
      "source_url": "https://ipindia.gov.in",
      "citation_text": "[1] The Patents Act, 1970 - Section 3(p) & Biological Resources\nAuthority: Indian Patent Office (IPO) / Parliament of India\nSection: Section 3(p)\nPage: 1\nVersion: 2005_amendment\nSource: https://ipindia.gov.in"
    }
  ],
  "disclaimer": "This response is for informational and decision-support purposes only..."
}
```

---

### 3. Debug Search Retrieval
**`POST /api/v1/search`**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/search" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "traditional knowledge patentability exclusions",
       "jurisdiction": "India",
       "topic": "Patent",
       "limit": 3
     }'
```

---

### 4. Submit Accuracy / Citation Feedback
**`POST /api/v1/feedback`**

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/feedback" \
     -H "Content-Type: application/json" \
     -d '{
       "rating": "helpful",
       "comment": "Accurately cited Section 3(p) and NBA approval requirement."
     }'
```

---

## 10. Verification, Audit & Test Suite

### 1. Statutory Source URL Live Audit
Audit the 5 canonical Indian statutory URLs (Patents Act, Trade Marks Act, Biological Diversity Act, Ayurveda Aahar Regulations, Drugs & Cosmetics Act) with zero external dependencies:
```bash
python scripts/check_source_urls.py
```
Expected output: All 5 statutory endpoints verified with HTTP 200.

### 2. SIH Acceptance Audit Test Suite (16 Points)
Run the dedicated audit test suite covering all compliance requirements (official URLs, unverified URL rejection, notice header verification, no hardcoded routing flags, claim-level citation validation, conditional language, multilingual queries, insufficient evidence admission, and the 4 domain functional questions):
```bash
pytest -v tests/test_audit_requirements.py
```

### 3. Full Automated Test Suite (43 Tests)
Execute all test modules:
```bash
pytest -v
```
All **43 tests** across 8 test suites will verify:
- Complete 16-point SIH Audit Requirements (`test_audit_requirements.py`)
- Grounded conversational responses and product context (`test_chat.py`)
- Claim-level citation mapping and anti-hallucination guardrails (`test_citations.py`)
- Classical ASU vs. Proprietary vs. Ayurveda Aahar classification with conditional legal language (`test_classification.py`)
- Document ingestion and chunk retrieval (`test_documents.py`)
- API health and database connectivity (`test_health.py`)
- Strict jurisdictional isolation and missing jurisdiction prompts (`test_jurisdiction.py`)
- Hybrid semantic retrieval and filtering (`test_rag.py`)

---

## 11. Troubleshooting & Common Errors

1. **`Port 8000 already in use`**:
   Specify a different port when running Uvicorn:
   `uvicorn app.main:app --reload --port 8001`
2. **`Docker not running / Qdrant refused connection`**:
   Do not worry. The backend has an automatic local fallback mechanism that saves vectors to `./qdrant_storage` and database records to `./ip_sakti.db`.
3. **`Pydantic ValidationError`**:
   Inspect the OpenAPI docs at `/docs` to ensure your request body JSON matches the expected schema.
4. **`Insufficient Evidence returned for a question`**:
   This is by design. If the question asks about a statutory rule not indexed in `data/documents/`, the system will refuse to guess. You can ingest the relevant statute via `POST /api/v1/documents/ingest` or `scripts/ingest_documents.py`.

---

## 12. Frontend Integration

This backend is designed to connect seamlessly with the React + Vite frontend at `https://github.com/rinasingh86961-cpu/ip-sakti-sahayak-frontend.git`.
CORS is preconfigured for `http://localhost:5173` and `http://localhost:3000`. Simply configure your frontend `.env` with:
```ini
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```
