# 📚 IAT Book Generator (Final)

> **100% Local** · No API keys required · Runs on CPU + GPU (optional)

An AI-powered book generator for the **IISER Aptitude Test (IAT)** preparation. It ingests your JEE, NEET, and NCERT reference PDFs into a local vector database, then uses a local LLM (Ollama) to synthesize original, LaTeX-formatted study chapters — completely offline.

This is the **clean, combined final version** of `iat_book_generator` (v1) and `iat_book_generator_v2` (v2/v3/v4), with all improvements merged into a single well-structured project.

---

## ✨ Features

- 📄 **PDF Ingestion** — Reads JEE, NEET, NCERT, and custom org books
- 🧠 **Local RAG** — ChromaDB vector store + HuggingFace embeddings (no API key)
- 🖊️ **Chapter Generation** — Full LaTeX chapters with:
  - Title page, Learning Objectives, TikZ Mind Map
  - Detailed Theory (definitions, examples, equations)
  - Year-wise Analysis Table (2021–2024)
  - 5 MCQ Practice Questions
- 🖼️ **Diagram Extraction** — Extracts meaningful figures from PDFs
- 🔁 **Auto-retry + Validation** — Validates LaTeX structure; retries on failure
- 📦 **JSON Artifact** — Each chapter exports a metadata JSON alongside the `.tex`

---

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running

```bash
# Start Ollama
ollama serve

# Create the custom IAT writer model
ollama create iat-writer -f Modelfile
```

### 2. Install Dependencies

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Add Your Source PDFs

Place your PDFs in the correct subfolders:

```
source_data/
├── jee_pcm/          ← JEE Physics/Chemistry/Maths PDFs
├── neet_bio/         ← NEET Biology PDFs
├── ncert/
│   ├── physics/      ← NCERT Physics PDFs
│   ├── chemistry/    ← NCERT Chemistry PDFs
│   ├── mathematics/  ← NCERT Mathematics PDFs
│   └── biology/      ← NCERT Biology PDFs
└── org_books/
    ├── class_11/     ← Your coaching module PDFs (class 11)
    └── class_12/     ← Your coaching module PDFs (class 12)
```

**File naming tip for modules:** `module_1.pdf`, `module_2.pdf` → auto-detected as ORG source.

### 4. Ingest PDFs

```bash
python src/ingest.py          # Fresh ingest (resets DB)
python src/ingest.py --append # Add more PDFs to existing DB
```

### 5. Generate a Chapter

```bash
# Basic usage
python src/generate.py "Kinematics"

# With filters (recommended for accuracy)
python src/generate.py "Cell Division" --subject Biology --grade 11

# With source filter
python src/generate.py "Thermodynamics" --source NCERT --source ORG

# Custom output filename
python src/generate.py "Optics" -o chapter_optics.tex
```

Output files are saved to `output/`:
- `chapter_<topic>.tex` — Full LaTeX document
- `chapter_<topic>.json` — Generation metadata + retrieval audit

### 6. Compile to PDF

```bash
pdflatex output/chapter_kinematics.tex
```

### 7. Extract Diagrams (Optional)

```bash
python src/diagram_extractor.py           # Extract from all source PDFs
python src/diagram_extractor.py --pdf path/to/file.pdf  # Single PDF
```

Extracted diagrams are saved to `output/assets/diagrams/` with a `manifest.csv`.

---

## 📁 Project Structure

```
Book_Generator_Final/
├── src/
│   ├── config.py            ← All tunable settings (chunk size, GPU layers, etc.)
│   ├── ingest.py            ← PDF → ChromaDB ingestion pipeline
│   ├── generate.py          ← Chapter generation (RAG + Ollama + LaTeX)
│   ├── prompts.py           ← LaTeX prompt templates and document preamble
│   └── diagram_extractor.py ← PDF diagram extraction utility
├── source_data/             ← Place your PDFs here (subfolders auto-detected)
├── output/                  ← Generated .tex and .json files
├── chroma_db/               ← Local vector database (auto-created, gitignored)
├── Modelfile                ← Custom Ollama model configuration
├── requirements.txt
├── .env.example             ← Template for optional API keys
└── README.md
```

---

## ⚙️ Configuration

Edit `src/config.py` to tune for your machine:

| Setting | Default | Description |
|---------|---------|-------------|
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Local embedding model |
| `RETRIEVAL_TOP_K` | `8` | Chunks retrieved per query |
| `LLM_MODEL` | `iat-writer` | Ollama model name |
| `LLM_GPU_LAYERS` | `10` | GPU layers (tune for your VRAM) |
| `LLM_MAX_RETRIES` | `3` | Generation retry attempts |
| `THEORY_MIN_CHARS` | `2200` | Minimum theory section length |

---

## 🔒 Privacy

This project runs **entirely on your machine**. No text, embeddings, or generated content is sent to any external server.

---

## 📄 License

MIT License — feel free to use, modify, and share.
