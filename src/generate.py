"""
IAT Book Generator — Chapter Generation Pipeline
=================================================
Usage:
  python src/generate.py "Kinematics"
  python src/generate.py "Cell Structure" --subject Biology --grade 11
  python src/generate.py "Thermodynamics" --source NCERT --source ORG -o chapter_thermo.tex
"""

import argparse
import gc
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    DB_DIR, EMBEDDING_MODEL, LLM_MAX_RETRIES, LLM_MODEL,
    LLM_TEMPERATURE, LLM_CONTEXT_WINDOW, OUTPUT_DIR,
    RETRIEVAL_POOL_MULTIPLIER, RETRIEVAL_TOP_K,
    THEORY_MIN_CHARS, THEORY_MIN_DEFINITIONS,
    THEORY_MIN_EQUATIONS, THEORY_MIN_EXAMPLES, THEORY_MIN_SUBSECTIONS,
)
from prompts import (
    CHAPTER_GENERATION_PROMPT, LATEX_PREAMBLE, LATEX_POSTAMBLE,
    REPAIR_PROMPT_TEMPLATE,
)


# ─────────────────────────────────────────────────────────────────────────────
# OLLAMA CLIENT
# ─────────────────────────────────────────────────────────────────────────────

def query_ollama(prompt: str, model: str = LLM_MODEL) -> str | None:
    """Send a prompt to a local Ollama model and return the response text."""
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model":       model,
                "prompt":      prompt,
                "stream":      False,
                "temperature": LLM_TEMPERATURE,
                "num_ctx":     LLM_CONTEXT_WINDOW,
            },
            timeout=600,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        print("   ❌ Cannot connect to Ollama! Run: ollama serve")
        return None
    except Exception as exc:
        print(f"   ❌ Ollama error: {exc}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LATEX VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def validate_latex(raw: str) -> tuple[str, list[str]]:
    """
    Clean up common LLM output issues and validate structure.
    Returns (cleaned_output, list_of_issues).
    """
    # Strip markdown fences
    cleaned = re.sub(r"```latex|```", "", raw).strip()

    # Force output to start at \chapter
    if r"\chapter{" in cleaned:
        cleaned = r"\chapter{" + cleaned.split(r"\chapter{", 1)[1]

    # Remove stray \end{document}
    cleaned = cleaned.replace(r"\end{document}", "").strip()

    issues: list[str] = []

    # Theory section checks
    theory_match = re.search(r"\\section\*\{Theory\}(.*?)(?=\\section|\Z)", cleaned, re.DOTALL)
    if not theory_match:
        issues.append("Missing \\section*{Theory}")
    else:
        body = theory_match.group(1)
        if len(body) < THEORY_MIN_CHARS:
            issues.append(f"Theory too short ({len(body)} chars, need {THEORY_MIN_CHARS})")
        if len(re.findall(r"\\subsection\*", body)) < THEORY_MIN_SUBSECTIONS:
            issues.append(f"Theory needs ≥{THEORY_MIN_SUBSECTIONS} \\subsection*")
        if len(re.findall(r"\\begin\{definition\}", body)) < THEORY_MIN_DEFINITIONS:
            issues.append(f"Theory needs ≥{THEORY_MIN_DEFINITIONS} definition environments")
        if len(re.findall(r"\\begin\{example\}", body)) < THEORY_MIN_EXAMPLES:
            issues.append(f"Theory needs ≥{THEORY_MIN_EXAMPLES} example environments")
        eq_count = len(re.findall(r"\\begin\{equation\}|\\\[", body))
        if eq_count < THEORY_MIN_EQUATIONS:
            issues.append(f"Theory needs ≥{THEORY_MIN_EQUATIONS} equations")

    # Mind map check
    if "\\begin{tikzpicture}" not in cleaned:
        issues.append("Missing TikZ mind map")

    # Analysis table check
    if "\\section*{Analysis Table}" not in cleaned:
        issues.append("Missing \\section*{Analysis Table}")

    return cleaned, issues


def build_repair_prompt(topic: str, original_prompt: str, issues: list[str], previous_output: str) -> str:
    return original_prompt + REPAIR_PROMPT_TEMPLATE.format(
        issues="\n".join(f"- {i}" for i in issues),
        previous_output=previous_output[:4000],
    )


# ─────────────────────────────────────────────────────────────────────────────
# RETRIEVAL
# ─────────────────────────────────────────────────────────────────────────────

SUBJECT_KEYWORDS = {
    "Physics":     ["motion", "force", "energy", "wave", "optics", "electr", "gravity", "thermo", "kinematic"],
    "Chemistry":   ["reaction", "bond", "element", "acid", "organic", "periodic", "molecule", "equilib"],
    "Biology":     ["cell", "gene", "dna", "photosynthesis", "respiration", "evolution", "organism", "enzyme"],
    "Mathematics": ["integral", "derivative", "matrix", "vector", "probability", "trigon", "complex", "limit"],
}

def infer_subject_from_topic(topic: str) -> str | None:
    tl = topic.lower()
    for subj, keywords in SUBJECT_KEYWORDS.items():
        if any(kw in tl for kw in keywords):
            return subj
    return None


def doc_matches(metadata: dict, subject: str | None, grade: str | None, sources: list[str] | None) -> bool:
    if subject and metadata.get("subject") != subject:
        return False
    if grade and str(metadata.get("grade", "")) != str(grade):
        return False
    if sources and metadata.get("source_type") not in sources:
        return False
    return True


def retrieve_context(vectorstore, topic: str, subject: str | None, grade: str | None, source_types: list[str] | None):
    pool_k = RETRIEVAL_TOP_K * RETRIEVAL_POOL_MULTIPLIER
    fallback_used = False

    # Try metadata-filtered search first
    filt = {}
    if subject:      filt["subject"]     = subject
    if grade:        filt["grade"]       = grade
    results = []
    if filt:
        try:
            results = vectorstore.similarity_search(topic, k=pool_k, filter=filt)
        except Exception:
            results = []

    # Fallback to broad search + Python-side filtering
    if len(results) < RETRIEVAL_TOP_K:
        fallback_used = True
        broad = vectorstore.similarity_search(topic, k=pool_k)
        filtered = [d for d in broad if doc_matches(d.metadata or {}, subject, grade, source_types)]
        results = filtered if len(filtered) >= RETRIEVAL_TOP_K else broad

    results = results[:RETRIEVAL_TOP_K]
    context_parts, records = [], []
    for i, doc in enumerate(results, 1):
        md = doc.metadata or {}
        context_parts.append(
            f"--- Source {i} [{md.get('source_type','?')} | {md.get('subject','?')} | "
            f"grade {md.get('grade','?')} | {md.get('file_name','?')}] ---\n{doc.page_content}\n"
        )
        records.append({
            "rank": i, "source_type": md.get("source_type"), "subject": md.get("subject"),
            "grade": md.get("grade"), "file_name": md.get("file_name"),
            "chapter_no": md.get("chapter_no"), "snippet": doc.page_content[:200],
        })

    return "\n".join(context_parts), records, {"fallback_used": fallback_used}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def generate_chapter(
    topic: str,
    output_filename: str | None = None,
    subject: str | None = None,
    grade: str | None = None,
    source_types: list[str] | None = None,
) -> None:

    print("=" * 55)
    print("  IAT BOOK GENERATOR — CHAPTER GENERATION")
    print("=" * 55)
    print(f"\n📝 Topic: {topic}\n")

    # Step 1: Load embeddings + DB
    print("⏳ Loading embedding model and ChromaDB...")
    embeddings  = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    vectorstore = Chroma(persist_directory=os.path.abspath(DB_DIR), embedding_function=embeddings)
    count = vectorstore._collection.count()
    print(f"   ✅ DB loaded ({count} chunks)\n")

    # Step 2: Auto-detect subject if not provided
    if not subject:
        subject = infer_subject_from_topic(topic)

    print(f"🔍 Retrieving top {RETRIEVAL_TOP_K} chunks "
          f"(subject={subject or 'any'}, grade={grade or 'any'}, sources={source_types or 'any'})...")
    context, retrieval_records, filter_info = retrieve_context(
        vectorstore, topic, subject, grade, source_types
    )
    if filter_info["fallback_used"]:
        print("   ⚠️  Broad fallback used (metadata filter had too few hits).")
    print(f"   ✅ Context: {len(context)} characters\n")

    del vectorstore; gc.collect()

    # Step 3: Generate with retry + validation
    prompt = CHAPTER_GENERATION_PROMPT.format(topic=topic, context=context)
    print(f"🖊️  Sending to {LLM_MODEL} via Ollama...")

    latex_content, issues, validation_passed = None, [], False
    active_prompt = prompt

    for attempt in range(1, LLM_MAX_RETRIES + 1):
        print(f"   🔁 Attempt {attempt}/{LLM_MAX_RETRIES}")
        raw = query_ollama(active_prompt)
        if not raw:
            continue
        cleaned, issues = validate_latex(raw)
        latex_content = cleaned
        if not issues:
            validation_passed = True
            print("   ✅ Validation passed.")
            break
        print(f"   ⚠️  Issues: {', '.join(issues)}")
        active_prompt = build_repair_prompt(topic, prompt, issues, raw)

    if not latex_content:
        print("\n❌ Generation failed. Is Ollama running? (ollama serve)")
        return
    if not validation_passed:
        print("   ⚠️  Saving best-effort output (validation not fully passed).")

    # Step 4: Save .tex + .json artifacts
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not output_filename:
        safe = topic.lower().replace("chapter ", "").strip()
        safe = safe.replace(" ", "_").replace("/", "_")[:40]
        output_filename = f"chapter_{safe}.tex"

    tex_path  = os.path.join(OUTPUT_DIR, output_filename)
    stem      = os.path.splitext(output_filename)[0]
    json_path = os.path.join(OUTPUT_DIR, f"{stem}.json")

    with open(tex_path, "w", encoding="utf-8") as f:
        f.write(LATEX_PREAMBLE + "\n" + latex_content + "\n" + LATEX_POSTAMBLE)

    artifact = {
        "artifact_type": "iat_chapter",
        "schema_version": "2.0",
        "topic": topic,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": LLM_MODEL,
        "validation": {"passed": validation_passed, "issues": issues, "best_effort": not validation_passed},
        "retrieval": {"top_k": RETRIEVAL_TOP_K, "filters": filter_info, "chunks": retrieval_records},
        "paths": {"tex": os.path.abspath(tex_path), "json": os.path.abspath(json_path)},
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 55}")
    print(f"  ✨ CHAPTER GENERATED!")
    print(f"  Topic   : {topic}")
    print(f"  LaTeX   : {tex_path}")
    print(f"  JSON    : {json_path}")
    print(f"  Online  : NONE (100% local)")
    print(f"{'=' * 55}")
    print(f"\n  Compile to PDF:  pdflatex {tex_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate an IAT book chapter")
    parser.add_argument("topic", help="Topic to generate (e.g. 'Kinematics')")
    parser.add_argument("-o", "--output", default=None, help="Output .tex filename")
    parser.add_argument("--subject", choices=["Physics", "Chemistry", "Mathematics", "Biology"],
                        help="Filter retrieval by subject")
    parser.add_argument("--grade", help="Filter by class grade (e.g. 11 or 12)")
    parser.add_argument("--source", action="append", dest="sources",
                        help="Filter by source type (NCERT, ORG, JEE, NEET) — repeatable")
    args = parser.parse_args()
    generate_chapter(args.topic, args.output, subject=args.subject,
                     grade=args.grade, source_types=args.sources)
