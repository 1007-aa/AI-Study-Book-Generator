"""
IAT Book Generator — System Configuration
==========================================
Tuned for: Intel i7-1165G7 | 7.5 GB RAM | NVIDIA MX350 (2 GB VRAM)

Edit values here to tune performance for your machine.
All paths are resolved relative to the project root automatically.
"""

import os

# ──────────────────────────────────────────────
# EMBEDDING  (100% Local — CPU, no API key)
# ──────────────────────────────────────────────
EMBEDDING_MODEL      = "all-MiniLM-L6-v2"  # ~80 MB RAM footprint
EMBEDDING_BATCH_SIZE = 24                   # Safe for 7.5 GB RAM

# ──────────────────────────────────────────────
# CHUNKING
# ──────────────────────────────────────────────
CHUNK_SIZE    = 600   # Characters per chunk
CHUNK_OVERLAP = 80    # Overlap to preserve concept continuity

# ──────────────────────────────────────────────
# CHROMADB  (Local Vector Database)
# ──────────────────────────────────────────────
CHROMA_INSERT_BATCH       = 75  # Documents per batch insert
RETRIEVAL_TOP_K           = 8   # Chunks retrieved per query
RETRIEVAL_POOL_MULTIPLIER = 4   # Extra candidates fetched for metadata filtering

# ──────────────────────────────────────────────
# GENERATION QUALITY THRESHOLDS
# ──────────────────────────────────────────────
THEORY_MIN_CHARS       = 2200  # Min characters in Theory section
THEORY_MIN_SUBSECTIONS = 3     # Min \subsection* headings
THEORY_MIN_DEFINITIONS = 2     # Min \begin{definition} environments
THEORY_MIN_EXAMPLES    = 2     # Min \begin{example} environments
THEORY_MIN_EQUATIONS   = 2     # Min \begin{equation} or \[...\]

# ──────────────────────────────────────────────
# LLM  (Local via Ollama — 100% offline)
# ──────────────────────────────────────────────
LLM_MODEL          = "iat-writer"   # Custom Ollama model (see Modelfile)
LLM_GPU_LAYERS     = 10             # GPU layers — tune for your VRAM
LLM_CONTEXT_WINDOW = 4096           # KV-cache context window
LLM_CPU_THREADS    = 4              # Leaves threads for OS + ChromaDB
LLM_TEMPERATURE    = 0.2            # Low = consistent LaTeX output
LLM_MAX_RETRIES    = 3              # Generation + validation retry attempts

# ──────────────────────────────────────────────
# DIAGRAM EXTRACTION
# ──────────────────────────────────────────────
DIAGRAM_MIN_SIZE_BYTES = 10_000  # Ignore decorative images below this size

# ──────────────────────────────────────────────
# PATHS  (all relative to project root)
# ──────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DIR   = os.path.join(PROJECT_ROOT, "source_data")
DB_DIR       = os.path.join(PROJECT_ROOT, "chroma_db")
OUTPUT_DIR   = os.path.join(PROJECT_ROOT, "output")
DIAGRAM_DIR  = os.path.join(OUTPUT_DIR, "assets", "diagrams")
