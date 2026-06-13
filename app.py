import streamlit as st
import os
from pdf_processor import process_pdf
from summarizer import generate_summary, generate_keywords, generate_flashcards, generate_quiz, DEFAULT_MODELS
from fpdf import FPDF
import io

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="InsightPaper AI - Research Summarizer",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium dark theme and glassmorphic UI customization
st.markdown("""
<style>
    /* Main layout modifications */
    .stApp {
        background: linear-gradient(135deg, #0e1117 0%, #161a24 100%);
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Headers styling */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(90deg, #6366f1 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Glassmorphism containers */
    div.stAlert, div.css-1r6g72x, .st-emotion-cache-1r6g72x {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0b0d13 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }
    
    /* Button custom design */
    div.stButton > button {
        background: linear-gradient(90deg, #4f46e5 0%, #7c3aed 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }
    div.stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.4) !important;
    }
    
    /* Secondary buttons */
    .secondary-btn div.stButton > button {
        background: rgba(255, 255, 255, 0.05) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        box-shadow: none !important;
    }
    .secondary-btn div.stButton > button:hover {
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }
    
    /* Badge styling for keywords */
    .keyword-badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        color: #818cf8;
        border: 1px solid rgba(99, 102, 241, 0.3);
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 500;
        margin: 5px;
        font-size: 0.85rem;
        transition: all 0.2s ease;
    }
    .keyword-badge:hover {
        background: rgba(99, 102, 241, 0.25);
        border-color: #818cf8;
        transform: scale(1.05);
    }
    
    /* Interactive Flashcard */
    .flashcard {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
        border: 1px solid rgba(168, 85, 247, 0.2);
        border-radius: 16px;
        padding: 2.5rem;
        min-height: 200px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        margin: 1.5rem 0;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
    }
    .flashcard-header {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: #a78bfa;
        margin-bottom: 1rem;
    }
    .flashcard-content {
        font-size: 1.3rem;
        font-weight: 500;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# HELPERS FOR PDF EXPORT
# -----------------------------------------------------------------------------
def export_summary_to_pdf(summary_text, paper_title, mode):
    """
    Helper to generate a clean, readable PDF download file.
    """
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "InsightPaper AI - Document Summary", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 10, f"Source: {paper_title}", ln=True, align="C")
    pdf.cell(0, 5, f"Mode: {mode.replace('_', ' ').title()}", ln=True, align="C")
    pdf.ln(10)
    
    # Body text formatting
    pdf.set_font("Helvetica", "", 11)
    
    # Encode and clean lines to prevent character encoding issues
    # fpdf2 handles text wrapping via multi_cell
    for line in summary_text.split("\n"):
        # Replace common markdown headers/bold elements for clean PDF look
        cleaned_line = line.replace("**", "").replace("###", "  ").replace("##", "").replace("#", "")
        # Basic ASCII formatting
        cleaned_line = cleaned_line.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 7, cleaned_line)
        
    return pdf.output()

# -----------------------------------------------------------------------------
# SIDEBAR / CONFIGURATION
# -----------------------------------------------------------------------------
st.sidebar.markdown("<h2 style='text-align: center;'>InsightPaper AI</h2>", unsafe_allow_html=True)
st.sidebar.caption("Summarize, Extract Keywords, and Learn Faster")
st.sidebar.markdown("---")

# LLM Provider Configuration
st.sidebar.subheader("🔌 LLM Settings")
provider = st.sidebar.selectbox(
    "API Provider",
    ["Gemini", "Groq", "OpenAI"],
    help="Gemini and Groq offer generous free developer tiers."
)

# Model configuration based on provider
api_key_env = ""
model_options = []

if provider == "Gemini":
    api_key_env = os.getenv("GEMINI_API_KEY", "")
    model_options = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-3.5-flash", "gemini-2.0-flash"]
elif provider == "Groq":
    api_key_env = os.getenv("GROQ_API_KEY", "")
    model_options = ["llama3-8b-8192", "llama3-70b-8192", "mixtral-8x7b-32768", "gemma2-9b-it"]
elif provider == "OpenAI":
    api_key_env = os.getenv("OPENAI_API_KEY", "")
    model_options = ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]

api_key = st.sidebar.text_input(
    f"{provider} API Key",
    value=api_key_env,
    type="password",
    placeholder=f"Enter your {provider} API Key..."
)

model_name = st.sidebar.selectbox("LLM Model", model_options)

st.sidebar.markdown("---")

# OCR Path settings (Windows specific setup)
st.sidebar.subheader("⚙️ OCR & System Settings")
use_ocr = st.sidebar.toggle(
    "Force OCR (Scanned PDF)", 
    help="Enable this if the PDF is scanned or direct text extraction fails."
)

with st.sidebar.expander("Windows OCR Paths (If needed)"):
    st.info("Required only for image/scanned PDFs.")
    tesseract_path = st.text_input(
        "Tesseract Exe Path",
        value=r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        help="Path to tesseract.exe. Install from UB-Mannheim's wiki."
    )
    poppler_path = st.text_input(
        "Poppler Bin Path",
        value=r"C:\poppler\bin",
        help="Path to Poppler bin folder (contains pdftoppm.exe)."
    )

# -----------------------------------------------------------------------------
# MAIN APP INTERFACE
# -----------------------------------------------------------------------------
st.title("🎓 InsightPaper AI")
st.markdown("##### Turn dense research articles and scanned documents into structured, actionable summaries and study tools.")

# 1. File Uploading
uploaded_file = st.file_uploader("Upload a PDF document", type=["pdf"])

if uploaded_file is not None:
    # Read bytes
    pdf_bytes = uploaded_file.read()
    
    st.markdown("### 🛠️ Summarization Settings")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        summary_mode = st.selectbox(
            "Summarization Mode",
            [
                ("Research Paper", "research_paper"),
                ("Student Notes", "student_notes"),
                ("Interview Prep", "interview_prep"),
                ("General Bullet Points", "general")
            ],
            format_func=lambda x: x[0]
        )
    with col2:
        num_keywords = st.slider("Number of Keywords", 5, 25, 15)
    with col3:
        num_questions = st.slider("Number of Quiz Questions", 0, 50, 5, help="Select 0 to disable quiz generation. High counts (e.g. 50) may increase processing time.")
        
    # Process file button
    if st.button("✨ Process and Analyze Document"):
        if not api_key:
            st.error(f"Please provide a valid {provider} API Key in the sidebar.")
        else:
            with st.spinner("Step 1: Reading and extracting text from PDF..."):
                try:
                    extracted_pages, ocr_used = process_pdf(
                        pdf_bytes,
                        force_ocr=use_ocr,
                        tesseract_cmd=tesseract_path,
                        poppler_path=poppler_path
                    )
                    
                    full_text = "\n\n".join([page["text"] for page in extracted_pages])
                    total_pages = len(extracted_pages)
                    total_chars = len(full_text)
                    
                    if total_chars < 50:
                        st.warning(
                            "We extracted very little text from this PDF. "
                            "It might be a scanned document or image. Please try toggling 'Force OCR (Scanned PDF)' in the sidebar."
                        )
                        
                    # Save state
                    st.session_state["full_text"] = full_text
                    st.session_state["total_pages"] = total_pages
                    st.session_state["total_chars"] = total_chars
                    st.session_state["ocr_used"] = ocr_used
                    st.session_state["analysis_ready"] = True
                    
                    # Reset interactive indexes
                    st.session_state["flashcard_idx"] = 0
                    st.session_state["show_flashcard_back"] = False
                    st.session_state["quiz_answers"] = {}
                    st.session_state["quiz_submitted"] = False
                    
                except Exception as e:
                    st.error(f"Error during text extraction: {str(e)}")
                    st.info("If you enabled OCR, verify that Tesseract and Poppler paths are set correctly in the sidebar settings.")
                    st.session_state["analysis_ready"] = False
                    
            if st.session_state.get("analysis_ready", False):
                # Run LLM Summary & Keywords
                with st.spinner("Step 2: Generating summary with AI..."):
                    try:
                        summary = generate_summary(
                            full_text,
                            provider=provider,
                            api_key=api_key,
                            mode=summary_mode[1],
                            model_name=model_name
                        )
                        st.session_state["summary"] = summary
                    except Exception as e:
                        st.error(f"Summarizer failed: {str(e)}")
                        st.session_state["summary"] = None
                        
                with st.spinner("Step 3: Extracting keywords..."):
                    try:
                        keywords = generate_keywords(
                            full_text,
                            provider=provider,
                            api_key=api_key,
                            model_name=model_name,
                            num_keywords=num_keywords
                        )
                        st.session_state["keywords"] = keywords
                    except Exception:
                        st.session_state["keywords"] = []
                        
                with st.spinner("Step 4: Creating interactive flashcards..."):
                    try:
                        flashcards = generate_flashcards(
                            full_text,
                            provider=provider,
                            api_key=api_key,
                            model_name=model_name
                        )
                        st.session_state["flashcards"] = flashcards
                    except Exception:
                        st.session_state["flashcards"] = []
                        
                with st.spinner("Step 5: Formulating Practice MCQ Quiz..."):
                    try:
                        quiz = generate_quiz(
                            full_text,
                            provider=provider,
                            api_key=api_key,
                            model_name=model_name,
                            num_questions=num_questions
                        )
                        st.session_state["quiz"] = quiz
                    except Exception:
                        st.session_state["quiz"] = []
                        
                st.success("🎉 Analysis complete! View results below.")

    # -----------------------------------------------------------------------------
    # DISPLAY RESULTS
    # -----------------------------------------------------------------------------
    if st.session_state.get("analysis_ready", False):
        st.markdown("---")
        
        # Document Stats Card
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin-bottom: 20px;">
            <span style="font-weight: 600; color: #a78bfa;">📊 Document Insights:</span> &nbsp;&nbsp;
            📄 <b>Pages:</b> {st.session_state["total_pages"]} &nbsp;&nbsp;|&nbsp;&nbsp;
            🔤 <b>Characters:</b> {st.session_state["total_chars"]} &nbsp;&nbsp;|&nbsp;&nbsp;
            ⚙️ <b>Extraction Method:</b> {"OCR (Scanned/Image)" if st.session_state["ocr_used"] else "Direct Text"}
        </div>
        """, unsafe_allow_html=True)
        
        # Results Tabs
        tab_summary, tab_keywords, tab_flashcards, tab_quiz, tab_raw = st.tabs([
            "📝 AI Summary", 
            "🏷️ Key Terms", 
            "🗂️ Study Flashcards",
            "❓ Practice Quiz",
            "📄 Raw Text"
        ])
        
        # TAB 1: SUMMARY
        with tab_summary:
            if st.session_state.get("summary"):
                st.markdown(st.session_state["summary"])
                
                # Download actions
                st.markdown("<br>", unsafe_allow_html=True)
                dl_col1, dl_col2, _ = st.columns([1.5, 1.5, 5])
                
                with dl_col1:
                    # TXT download
                    st.download_button(
                        label="⬇️ Download as Text File",
                        data=st.session_state["summary"],
                        file_name=f"{uploaded_file.name}_summary.txt",
                        mime="text/plain"
                    )
                with dl_col2:
                    # PDF download
                    try:
                        pdf_bytes = export_summary_to_pdf(
                            st.session_state["summary"],
                            uploaded_file.name,
                            summary_mode[0]
                        )
                        st.download_button(
                            label="⬇️ Download as PDF",
                            data=pdf_bytes,
                            file_name=f"{uploaded_file.name}_summary.pdf",
                            mime="application/pdf"
                        )
                    except Exception as pdf_err:
                        st.caption(f"PDF exporter unavailable: {pdf_err}")
            else:
                st.warning("No summary was generated. Review your API configuration.")
                
        # TAB 2: KEYWORDS
        with tab_keywords:
            keywords = st.session_state.get("keywords", [])
            if keywords:
                st.markdown("### 🔑 Important Keywords & Concepts")
                st.write("Click keywords to search them or study concepts further.")
                
                badge_html = ""
                for kw in keywords:
                    badge_html += f'<div class="keyword-badge">{kw}</div>'
                st.markdown(badge_html, unsafe_allow_html=True)
            else:
                st.info("No keywords extracted.")
                
        # TAB 3: STUDY FLASHCARDS
        with tab_flashcards:
            flashcards = st.session_state.get("flashcards", [])
            if flashcards:
                st.markdown("### 🗂️ Active Recall Flashcards")
                st.write("Use flashcards to test your knowledge of key topics in this paper.")
                
                idx = st.session_state.get("flashcard_idx", 0)
                show_back = st.session_state.get("show_flashcard_back", False)
                
                # Card container
                card = flashcards[idx]
                card_side = "Back (Explanation)" if show_back else "Front (Question/Concept)"
                card_text = card["back"] if show_back else card["front"]
                
                st.markdown(f"""
                <div class="flashcard">
                    <div class="flashcard-header">Card {idx + 1} of {len(flashcards)} &nbsp;•&nbsp; {card_side}</div>
                    <div class="flashcard-content">{card_text}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Controls
                ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([1, 1, 1])
                
                with ctrl_col1:
                    # Prev Button
                    if st.button("⬅️ Previous Card") and idx > 0:
                        st.session_state["flashcard_idx"] = idx - 1
                        st.session_state["show_flashcard_back"] = False
                        st.rerun()
                with ctrl_col2:
                    # Flip Button
                    if st.button("🔄 Flip Card"):
                        st.session_state["show_flashcard_back"] = not show_back
                        st.rerun()
                with ctrl_col3:
                    # Next Button
                    if st.button("➡️ Next Card") and idx < len(flashcards) - 1:
                        st.session_state["flashcard_idx"] = idx + 1
                        st.session_state["show_flashcard_back"] = False
                        st.rerun()
            else:
                st.info("Flashcards not generated.")
                
        # TAB 4: PRACTICE MCQ QUIZ
        with tab_quiz:
            quiz = st.session_state.get("quiz", [])
            if quiz:
                st.markdown("### ❓ Document Comprehension Quiz")
                st.write("Test your understanding with these AI-generated multiple choice questions.")
                
                submitted = st.session_state.get("quiz_submitted", False)
                answers = st.session_state.get("quiz_answers", {})
                
                for i, q in enumerate(quiz):
                    st.markdown(f"#### Q{i+1}: {q['question']}")
                    
                    options = q["options"]
                    # Format as Option Label: Option Value
                    opt_list = [f"{k}: {v}" for k, v in options.items()]
                    
                    # Find previously selected index or default to 0
                    prev_selection = answers.get(i, None)
                    prev_index = 0
                    if prev_selection is not None:
                        for idx, opt in enumerate(opt_list):
                            if opt.startswith(prev_selection):
                                prev_index = idx
                                
                    user_select = st.radio(
                        f"Select your answer for Question {i+1}:",
                        opt_list,
                        index=prev_index,
                        key=f"q_{i}",
                        disabled=submitted
                    )
                    
                    # Save answer
                    selected_key = user_select.split(":")[0]
                    answers[i] = selected_key
                    
                    # If submitted, show correction
                    if submitted:
                        correct_key = q["answer"]
                        if selected_key == correct_key:
                            st.success(f"✅ Correct! ({correct_key})")
                        else:
                            st.error(f"❌ Incorrect. Your answer: {selected_key} | Correct answer: {correct_key}")
                        st.info(f"ℹ️ **Explanation:** {q['explanation']}")
                        
                    st.markdown("<hr style='border-top: 1px solid rgba(255,255,255,0.05);'>", unsafe_allow_html=True)
                    
                st.session_state["quiz_answers"] = answers
                
                if not submitted:
                    if st.button("📝 Submit Answers"):
                        st.session_state["quiz_submitted"] = True
                        st.rerun()
                else:
                    if st.button("🔄 Restart Quiz"):
                        st.session_state["quiz_submitted"] = False
                        st.session_state["quiz_answers"] = {}
                        st.rerun()
            else:
                if num_questions == 0:
                    st.info("Quiz is disabled. Set 'Number of Quiz Questions' to a value greater than 0 in the settings to generate a practice quiz.")
                else:
                    st.info("Quiz questions not generated. Verify API credentials or check settings.")
                
        # TAB 5: RAW TEXT
        with tab_raw:
            st.markdown("### 📄 Raw Extracted Text")
            st.write("This is the full plain text extracted from the document.")
            st.text_area("Extracted Text", st.session_state["full_text"], height=400)

else:
    # Landing UI if no file is uploaded
    st.markdown("<br><br>", unsafe_allow_html=True)
    l_col1, l_col2, l_col3 = st.columns([1, 2, 1])
    with l_col2:
        st.markdown("""
        <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); padding: 40px; border-radius: 16px; text-align: center; box-shadow: 0 15px 35px rgba(0,0,0,0.2);">
            <div style="font-size: 4rem; margin-bottom: 20px;">📚</div>
            <h3 style="margin-bottom: 15px;">Get Started</h3>
            <p style="color: #94a3b8; font-size: 1.1rem; line-height: 1.6;">
                Upload a research paper, journal article, textbook chapter, or scanned notes in PDF format.
                InsightPaper AI will analyze the content and generate key insights, cards, and quizzes.
            </p>
            <div style="margin-top: 25px; font-size: 0.9rem; color: #64748b;">
                💡 <i>TIPS: Provide your API key in the sidebar first. Toggle OCR if uploading scanned documents or images.</i>
            </div>
        </div>
        """, unsafe_allow_html=True)
