# InsightPaper AI - Research Summarizer

A modern, high-quality, feature-rich web application to summarize research papers, textbook chapters, and scanned notes. Built with Python, Streamlit, and advanced LLMs (Gemini, Groq, and OpenAI).

## Features

- **Multi-Engine Support**: Seamlessly use Gemini API (free tier), Groq API (free tier), or OpenAI API.
- **Smart PDF Text Extraction**:
  - Automatically extracts text from digital/typed PDFs.
  - Automatically detects scanned pages/images and converts them to text via **Tesseract OCR**.
- **Interactive Reading Modes**:
  - **Research Paper**: Formats summary under Problem, Methodology, Results, Limitations, and Future Work.
  - **Student Notes**: Formats concise review sheets and formats mathematical formulas in LaTeX ($$formula$$).
  - **Interview Prep**: Simplifies content and generates 10 defense/interview questions with answers.
- **Study & Comprehension Tools**:
  - **Keyword Extraction**: Identifies and badges 15 important concepts.
  - **Recall Flashcards**: Interactive digital cards to flip (Question/Answer).
  - **Practice MCQ Quiz**: Generates a 5-question multiple-choice quiz with automatic grading and rationale.
- **Exporting Options**:
  - Download summary directly as plain text (`.txt`) or a formatted PDF (`.pdf`).

---

## Installation & Setup

### 1. Clone or Open the Workspace

Open a terminal and navigate to the project directory:
```bash
cd C:\Users\soura\.gemini\antigravity\scratch\pdf-summarizer
```

### 2. Create and Activate Virtual Environment

If you have `uv` installed (recommended):
```bash
uv venv .venv
.venv\Scripts\activate
```

Or using standard Python:
```bash
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

---

## OCR Setup (For Scanned PDFs)

To support scanned PDFs or handwriting, you need to install two systems on Windows and configure their paths in the sidebar of the app:

### 1. Tesseract OCR (Windows)
1. Download the installer from the [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki).
2. Install it. The default installation path is usually:
   `C:\Program Files\Tesseract-OCR\tesseract.exe`
3. Enter this path into the **Tesseract Exe Path** field in the app sidebar.

### 2. Poppler (Windows)
1. Download the latest pre-compiled binaries for Windows (e.g. from [GitHub poppler-windows](https://github.com/oschwartz10612/poppler-windows/releases)).
2. Extract the ZIP file.
3. Locate the `bin` directory (which contains `pdftoppm.exe`, etc.), for example:
   `C:\poppler\bin`
4. Enter this path into the **Poppler Bin Path** field in the app sidebar.

---

## Running the Application

Start the Streamlit development server:
```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`.
