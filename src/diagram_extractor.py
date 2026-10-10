"""
IAT Book Generator — Diagram Extractor
=======================================
Extracts meaningful diagrams from source PDFs and saves them with metadata.
Usage:
  python src/diagram_extractor.py                  # extract from all source PDFs
  python src/diagram_extractor.py --pdf path/to/file.pdf
"""

import argparse
import csv
import glob
import hashlib
import os
import sys

import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(__file__))
from config import DIAGRAM_DIR, DIAGRAM_MIN_SIZE_BYTES, OUTPUT_DIR, SOURCE_DIR


def extract_diagrams_from_pdf(pdf_path: str, source_name: str, output_dir: str) -> list[dict]:
    """Extract meaningful images from a PDF, skip tiny decorative ones."""
    os.makedirs(output_dir, exist_ok=True)
    doc     = fitz.open(pdf_path)
    results = []

    for page_num in range(len(doc)):
        for img_info in doc[page_num].get_images(full=True):
            xref        = img_info[0]
            base_image  = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext   = base_image["ext"]

            if len(image_bytes) < DIAGRAM_MIN_SIZE_BYTES:
                continue  # skip decorative / tiny images

            img_hash = hashlib.md5(image_bytes).hexdigest()[:12]
            filename = f"{source_name}_p{page_num + 1}_{img_hash}.{image_ext}"
            filepath = os.path.join(output_dir, filename)

            with open(filepath, "wb") as f:
                f.write(image_bytes)

            results.append({
                "filename":    filename,
                "filepath":    filepath,
                "source_pdf":  pdf_path,
                "source_name": source_name,
                "page_number": page_num + 1,
                "size_bytes":  len(image_bytes),
                "format":      image_ext,
                "hash":        img_hash,
            })

    doc.close()
    return results


def save_manifest(diagrams: list[dict], output_dir: str) -> None:
    if not diagrams:
        return
    manifest_path = os.path.join(output_dir, "manifest.csv")
    fieldnames = ["filename", "filepath", "source_pdf", "source_name",
                  "page_number", "size_bytes", "format", "hash"]
    with open(manifest_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(diagrams)
    print(f"✅ Manifest saved: {manifest_path}")


def run_extraction(pdf_path: str | None = None) -> None:
    diag_dir = os.path.abspath(DIAGRAM_DIR)
    all_diagrams: list[dict] = []

    if pdf_path:
        pdfs = [pdf_path]
    else:
        pdfs = glob.glob(os.path.join(SOURCE_DIR, "**/*.pdf"), recursive=True)

    if not pdfs:
        print("❌ No PDFs found.")
        return

    print(f"🔍 Extracting diagrams from {len(pdfs)} PDF(s)...")
    for path in pdfs:
        source_name = os.path.splitext(os.path.basename(path))[0]
        diagrams    = extract_diagrams_from_pdf(path, source_name, diag_dir)
        print(f"   📄 {os.path.basename(path)} → {len(diagrams)} diagrams extracted")
        all_diagrams.extend(diagrams)

    save_manifest(all_diagrams, diag_dir)
    total_mb = sum(d["size_bytes"] for d in all_diagrams) / 1_048_576
    print(f"\n✨ Done! {len(all_diagrams)} diagrams ({total_mb:.1f} MB) saved to:\n   {diag_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract diagrams from source PDFs")
    parser.add_argument("--pdf", default=None, help="Extract from a single PDF (optional)")
    args = parser.parse_args()
    run_extraction(pdf_path=args.pdf)
