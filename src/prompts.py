"""
IAT Book Generator — LaTeX Prompts & Preamble
===============================================
Central store for all prompt templates and LaTeX document wrappers.
"""

# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHAPTER GENERATION PROMPT
# ─────────────────────────────────────────────────────────────────────────────

CHAPTER_GENERATION_PROMPT = r"""
You are a senior science author writing a premium IISER Aptitude Test (IAT) preparation book.

## STRICT RULES:
1. **DO NOT copy any sentence from the source material verbatim.** Synthesize and re-explain concepts in your own voice.
2. **Focus on conceptual depth**, not rote memorization.
3. **Output ONLY valid LaTeX code**. Do NOT include conversational filler and do NOT wrap output in markdown fences (no ```latex).
4. **Use appropriate LaTeX environments:**
   - \begin{{definition}}...\end{{definition}} for definitions.
   - \begin{{example}}...\end{{example}} for illustrative examples.
   - \begin{{equation}}...\end{{equation}} for mathematical formulas.
5. **NEVER output Markdown tables or Markdown bullets**. Use only LaTeX environments.
6. **Do not add** \documentclass, \usepackage, \begin{{document}}, or \end{{document}}.
7. **If year-wise data is missing**, write "Insufficient data" in analysis table cells instead of inventing values.
8. **Never use** \link, markdown tables, or fake image paths.

## PAGE LAYOUT (one section per page — mandatory):
Use \clearpage after every major section block.

Structure skeleton (follow exactly):

\chapter{{<number>. <name>}}
\thispagestyle{{plain}}
\vspace*{{\fill}}
\begin{{center}}
{{\Large \textbf{{IAT Preparation Book}}}}\\[1.5em]
{{\Huge \textbf{{<Chapter Title>}}}}\\[0.75em]
{{\large Chapter <number>}}
\end{{center}}
\vspace*{{\fill}}
\clearpage

\section*{{Learning Objectives}}
\begin{{itemize}} ... 4--6 \item lines ... \end{{itemize}}
\clearpage

\section*{{Concept Mind Map}}
... TikZ mind map (see rules below) ...
\clearpage

\section*{{Analysis Table}}
\begin{{tabular}}{{|l|c|c|c|c|c|}}} with header: Topic & 2021 & 2022 & 2023 & 2024 & Trend
\clearpage

\section*{{Theory}}
... full textbook-style explanation (multiple pages allowed) ...
\clearpage

\section*{{PYQs \& Practice}}
... exactly 5 MCQs (1.--5.) with (a)--(d) and one-line solutions ...

## THEORY SECTION REQUIREMENTS (mandatory):
- Use \subsection*{{}} for each major topic (at least 3 subsections).
- Each subsection must include: intuitive intro, formal \begin{{definition}}, key relations in \begin{{equation}}, at least one \begin{{example}} with step-by-step reasoning, and exam tips in an itemize list.
- Include **at least 2** definition environments, **2** example environments, **2** numbered equations.
- Write enough for a Class 11–12 student to learn without other books.

## TikZ MIND MAP RULES:
\begin{{tikzpicture}}[mindmap, grow cyclic, every node/.style={{concept}},
  concept color=iatblue!80,
  level 1/.append style={{level distance=4.5cm, sibling angle=60}},
  level 2/.append style={{level distance=3cm, sibling angle=45}}]
  \node{{<Central Topic>}}
    child {{ node {{<Sub-topic 1>}} }}
    child {{ node {{<Sub-topic 2>}}
      child {{ node {{<Detail A>}} }}
      child {{ node {{<Detail B>}} }}
    }}
    child {{ node {{<Sub-topic 3>}} }}
    child {{ node {{<Sub-topic 4>}} }}
    child {{ node {{<Sub-topic 5>}} }};
\end{{tikzpicture}}
- Central node = chapter topic.
- At least 5 level-1 children, 2 level-2 children.
- Node labels: 1–4 words, no \link or URLs.

## TOPIC TO WRITE ABOUT:
{topic}

## REFERENCE MATERIAL (factual reference only — do NOT copy verbatim):
{context}

## OUTPUT:
Begin immediately with \chapter{{}}. Return only chapter-body LaTeX.
"""

# ─────────────────────────────────────────────────────────────────────────────
# REPAIR PROMPT  (used when validation fails)
# ─────────────────────────────────────────────────────────────────────────────

REPAIR_PROMPT_TEMPLATE = r"""
The LaTeX chapter you generated has the following issues:
{issues}

Here is your previous output:
---
{previous_output}
---

Please fix ONLY the issues listed above and return the corrected complete chapter LaTeX.
Do not change anything else. Begin immediately with \chapter{{}}.
"""

# ─────────────────────────────────────────────────────────────────────────────
# LATEX DOCUMENT WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

LATEX_PREAMBLE = r"""\documentclass[12pt, a4paper]{book}

% ── Core Packages ──
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath, amssymb, amsthm}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{enumitem}
\usepackage[margin=2.5cm]{geometry}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{tikz}
\usetikzlibrary{mindmap,trees}
\usepackage{needspace}

% ── Color Palette ──
\definecolor{iatblue}{RGB}{25, 84, 150}
\definecolor{iatgray}{RGB}{100, 100, 100}
\definecolor{iatgreen}{RGB}{34, 139, 34}
\definecolor{iatorange}{RGB}{210, 105, 30}
\definecolor{iatpurple}{RGB}{128, 0, 128}
\definecolor{iatred}{RGB}{178, 34, 34}

% ── Page Style ──
\pagestyle{fancy}
\fancyhf{}
\fancyhead[LE,RO]{\thepage}
\fancyhead[RE,LO]{\leftmark}
\renewcommand{\headrulewidth}{0.4pt}

% ── Theorem Environments ──
\newtheorem{definition}{Definition}[chapter]
\newtheorem{theorem}{Theorem}[chapter]
\newtheorem{example}{Example}[chapter]

% ── Title ──
\title{\textbf{\Huge IAT Preparation Book} \\ \Large A Comprehensive Guide for IISER Aptitude Test}
\author{Generated with AI-Assisted Synthesis}
\date{\today}

\begin{document}
\maketitle
\tableofcontents
\newpage

"""

LATEX_POSTAMBLE = r"""
\end{document}
"""
