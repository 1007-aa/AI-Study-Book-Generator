"""
IAT Book Generator — Ingestion Pipeline
========================================
Reads PDFs from source_data/, chunks them, embeds them LOCALLY
using HuggingFace sentence-transformers, and stores in ChromaDB.

Source folders recognised automatically:
  source_data/jee_pcm/        → source_type = JEE
  source_data/neet_bio/       → source_type = NEET
  source_data/ncert/<subject>/→ source_type = NCERT
  source_data/org_books/class_<N>/ → source_type = ORG

100% LOCAL — No data leaves your machine.
Usage:
  python src/ingest.py            # reset DB then ingest
  python src/ingest.py --append   # add to existing DB
"""

import gc
import glob
import os
import re
import shutil
import sys

import fitz  # PyMuPDF
from langchain.schema import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_INSERT_BATCH,
    DB_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    SOURCE_DIR,
)


# ─────────────────────────────────────────────────────────────────────────────
# PDF LOADING  (PyMuPDF — preserves layout better than PyPDFLoader)
# ─────────────────────────────────────────────────────────────────────────────

def load_pdf_with_fitz(file_path: str) -> list[Document]:
    """Load a PDF and return one Document per page with clean text."""
    pdf = fitz.open(file_path)
    docs = []

    for page_num in range(len(pdf)):
        page = pdf[page_num]
        blocks = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
        page_lines = []

        for block in blocks:
            if block.get("type") != 0:  # skip non-text blocks
                continue
            for line in block.get("lines", []):
                line_text = ""
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    if line_text and span.get("flags", 0) & 16:  # superscript
                        line_text = line_text.rstrip() + "_" + text + " "
                    else:
                        line_text += text + " "
                stripped = line_text.strip()
                if stripped:
                    page_lines.append(stripped)

        docs.append(Document(
            page_content="\n".join(page_lines),
            metadata={"page": page_num, "source": file_path},
        ))

    pdf.close()
    return docs


# ─────────────────────────────────────────────────────────────────────────────
# METADATA INFERENCE
# ─────────────────────────────────────────────────────────────────────────────

def infer_source(file_path: str) -> str:
    lp = file_path.lower()
    if "jee_pcm" in lp:    return "JEE"
    if "neet_bio" in lp:   return "NEET"
    if "ncert"    in lp:   return "NCERT"
    if "org_books" in lp:  return "ORG"
    return "General"


def infer_subject(file_path: str, fname: str) -> str:
    lp, ln = file_path.lower(), fname.lower()
    # prefer folder-based detection
    for subj in ["physics", "chemistry", "mathematics", "biology"]:
        if f"/{subj}/" in lp or f"\\{subj}\\" in lp:
            return subj.capitalize()
    if "/maths/" in lp or "\\maths\\" in lp:
        return "Mathematics"
    # fallback: filename keywords
    for subj in ["physics", "chemistry", "mathematics", "biology"]:
        if subj in ln:
            return subj.capitalize()
    if "maths" in ln or re.search(r"(^|_)math(_|$)", ln):
        return "Mathematics"
    return "Unknown"


def infer_grade(file_path: str) -> str | None:
    m = re.search(r"class[_-]?(\d{2})", file_path.lower())
    return m.group(1) if m else None


def infer_chapter_metadata(fname: str) -> tuple[str | None, str]:
    lowered = fname.lower().replace(".pdf", "")
    match = re.search(r"(?:^|_)ch(?:apter)?[_-]?(\d{1,2})(?:_|$)", lowered)
    if match:
        chapter_no   = match.group(1).zfill(2)
        chapter_name = lowered[match.end():].strip("_- ") or lowered
    else:
        chapter_no   = None
        chapter_name = lowered
    return chapter_no, chapter_name.replace("_", " ").replace("-", " ").strip()


def infer_org_module(fname: str) -> str | None:
    m = re.search(r"modules?_(\d+)", fname.lower().replace(".pdf", ""))
    return m.group(1) if m else None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def ingest_data(reset_db: bool = True) -> None:
    print("=" * 55)
    print("  IAT BOOK GENERATOR — LOCAL INGESTION PIPELINE")
    print("=" * 55)

    # Step 1: Embedding model
    print(f"\n⏳ Loading embedding model: {EMBEDDING_MODEL}")
    print("   (Runs on CPU — no data sent online)")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        encode_kwargs={"batch_size": EMBEDDING_BATCH_SIZE},
    )
    print("✅ Embedding model loaded.\n")

    # Step 2: Find PDFs
    source_path = os.path.abspath(SOURCE_DIR)
    print(f"🔍 Scanning: {source_path}")
    files = glob.glob(os.path.join(SOURCE_DIR, "**/*.pdf"), recursive=True)
    if not files:
        print("❌ No PDF files found! Add PDFs to the source_data/ subfolders.")
        return
    print(f"   Found {len(files)} file(s).\n")

    # Step 3: Optional DB reset
    db_path = os.path.abspath(DB_DIR)
    if reset_db and os.path.isdir(db_path):
        print(f"🧹 Resetting existing ChromaDB at: {db_path}")
        shutil.rmtree(db_path, ignore_errors=True)

    # Step 4: Load and tag PDFs
    all_docs: list[Document] = []
    for file_path in files:
        fname = os.path.basename(file_path)
        print(f"📖 Loading: {fname}")
        source       = infer_source(file_path)
        subject      = infer_subject(file_path, fname)
        grade        = infer_grade(file_path)
        chapter_no, chapter_name = infer_chapter_metadata(fname)
        org_module   = infer_org_module(fname) if source == "ORG" else None

        try:
            pages = load_pdf_with_fitz(file_path)
            for page in pages:
                page.metadata.update({
                    "source_type":  source,
                    "subject":      subject,
                    "file_name":    fname,
                    "chapter_no":   chapter_no,
                    "chapter_name": chapter_name,
                })
                if grade:      page.metadata["grade"]      = grade
                if org_module: page.metadata["org_module"] = org_module
            all_docs.extend(pages)
            extra = f"  |  Module: {org_module}" if org_module else ""
            print(f"   ✅ {len(pages)} pages  |  {source}  |  {subject}  |  Grade: {grade or '—'}{extra}")
        except Exception as exc:
            print(f"   ❌ Error loading {fname}: {exc}")

    if not all_docs:
        print("\n❌ No text could be extracted from the PDFs.")
        return

    # Step 5: Chunk
    print(f"\n✂️  Splitting {len(all_docs)} pages → chunks "
          f"(size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP, add_start_index=True
    )
    chunks = splitter.split_documents(all_docs)
    print(f"   ✅ {len(chunks)} chunks created.\n")
    del all_docs; gc.collect()

    # Step 6: Embed + store in ChromaDB (batched)
    print(f"💾 Storing in ChromaDB: {db_path}")
    vectorstore = None
    for i in range(0, len(chunks), CHROMA_INSERT_BATCH):
        batch = chunks[i : i + CHROMA_INSERT_BATCH]
        n     = (i // CHROMA_INSERT_BATCH) + 1
        total = (len(chunks) + CHROMA_INSERT_BATCH - 1) // CHROMA_INSERT_BATCH
        if i == 0:
            vectorstore = Chroma.from_documents(batch, embeddings, persist_directory=db_path)
        else:
            vectorstore.add_documents(batch)
        print(f"   📦 Batch {n}/{total} ({len(batch)} chunks)")
        gc.collect()

    count = vectorstore._collection.count()
    print(f"\n{'=' * 55}")
    print(f"  ✨ INGESTION COMPLETE!")
    print(f"  Chunks stored  : {count}")
    print(f"  DB location    : {db_path}")
    print(f"  Data sent online: NONE (100% local)")
    print(f"{'=' * 55}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest PDFs into ChromaDB for IAT generation")
    parser.add_argument("--append", action="store_true",
                        help="Add to existing DB instead of resetting it")
    args = parser.parse_args()
    ingest_data(reset_db=not args.append)
