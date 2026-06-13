import os
import json
import re
from openai import OpenAI
from groq import Groq
from google import genai
from google.genai import types

# Default Models
DEFAULT_MODELS = {
    "Gemini": "gemini-2.5-flash",
    "Groq": "llama3-8b-8192",
    "OpenAI": "gpt-4o-mini"
}

def split_text_into_chunks(text, max_chars=120000):
    """
    Splits text into chunks of maximum size (default ~30k tokens/120k characters)
    preserving paragraph boundaries.
    """
    if len(text) <= max_chars:
        return [text]
        
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    
    for para in paragraphs:
        # If a single paragraph is larger than max_chars, split by sentences
        if len(para) > max_chars:
            sentences = re.split(r'(?<=[.!?]) +', para)
            for sentence in sentences:
                if current_length + len(sentence) > max_chars:
                    if current_chunk:
                        chunks.append("\n\n".join(current_chunk))
                    current_chunk = [sentence]
                    current_length = len(sentence)
                else:
                    current_chunk.append(sentence)
                    current_length += len(sentence)
        elif current_length + len(para) > max_chars:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_length = len(para)
        else:
            current_chunk.append(para)
            current_length += len(para) + 2  # plus paragraph spacing
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks

def call_llm(provider, api_key, system_prompt, user_prompt, model_name=None, json_mode=False):
    """
    Low-level client dispatcher for Gemini, Groq, and OpenAI.
    """
    if not model_name:
        model_name = DEFAULT_MODELS.get(provider)
        
    if provider == "Gemini":
        try:
            client = genai.Client(api_key=api_key)
            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
            )
            if json_mode:
                config.response_mime_type = "application/json"
                
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=config
            )
            return response.text
        except Exception as e:
            raise e
            
    elif provider == "Groq":
        client = Groq(api_key=api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        args = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3
        }
        if json_mode:
            args["response_format"] = {"type": "json_object"}
        chat_completion = client.chat.completions.create(**args)
        return chat_completion.choices[0].message.content
        
    elif provider == "OpenAI":
        client = OpenAI(api_key=api_key)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        args = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3
        }
        if json_mode:
            args["response_format"] = {"type": "json_object"}
        chat_completion = client.chat.completions.create(**args)
        return chat_completion.choices[0].message.content
        
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

def get_system_prompt_for_mode(mode):
    """
    Returns custom system instructions for different summary modes.
    """
    if mode == "research_paper":
        return (
            "You are a brilliant research paper summarizer. Summarize the provided document structure and clearly define:\n"
            "- **Problem**: What core issue is the paper addressing?\n"
            "- **Methodology**: What approach, models, data, or experiments were used?\n"
            "- **Results**: What were the main findings and achievements?\n"
            "- **Limitations**: What are the limitations or potential weaknesses of the work?\n"
            "- **Future Work**: What potential next steps or research directions are proposed?\n"
            "Keep the formatting clean, professional, and dense with key details. Use Markdown formatting."
        )
    elif mode == "student_notes":
        return (
            "You are an expert academic tutor. Create short, clear revision notes for a student.\n"
            "- Extract key concepts and definitions.\n"
            "- Highlight any formulas or equations explicitly using LaTeX markdown notation like $$formula$$ or $formula$.\n"
            "- Group details under logical headers.\n"
            "- List important bullet points and key takeaways.\n"
            "Format the output using modern, clear, and scannable markdown formatting."
        )
    elif mode == "interview_prep":
        return (
            "You are a tech lead preparing a candidate for a technical review or interview on this document.\n"
            "- First, explain the core content and ideas of the document in a very simple, intuitive 'Explain Like I'm 5' way (maximum 3 paragraphs).\n"
            "- Then, generate 10 highly likely interview or technical defense questions based on this document, along with a concise, high-scoring model answer for each.\n"
            "Format the output cleanly in markdown with collapsible details if possible or clear bold headers."
        )
    else:  # general mode
        return (
            "You are a precise document summarizer. Summarize the key findings, arguments, and conclusions of the document in a concise, bullet-point list. Use Markdown format."
        )

def generate_summary(text, provider, api_key, mode="research_paper", model_name=None):
    """
    Generates summary for the PDF content, handling chunking and map-reduce if needed.
    """
    chunks = split_text_into_chunks(text)
    system_prompt = get_system_prompt_for_mode(mode)
    
    if len(chunks) == 1:
        # Small enough for single prompt
        user_prompt = f"Analyze the following text and generate the requested summary:\n\n{chunks[0]}"
        return call_llm(provider, api_key, system_prompt, user_prompt, model_name)
    
    # Map stage: Summarize each chunk
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        chunk_prompt = f"This is part {i+1} of {len(chunks)} of a larger document. Summarize this section:\n\n{chunk}"
        # Use a simpler intermediate summarization prompt
        chunk_summary = call_llm(
            provider, 
            api_key, 
            "You are an assistant summarizing a section of a larger paper. Extract all core arguments, facts, and conclusions.", 
            chunk_prompt, 
            model_name
        )
        chunk_summaries.append(chunk_summary)
        
    # Reduce stage: Combine summaries
    combined_summaries = "\n\n=== Section Summary ===\n\n".join(chunk_summaries)
    reduce_prompt = f"Below are the summaries of different sections of a research paper. Create a cohesive, final summary using the requested format:\n\n{combined_summaries}"
    
    return call_llm(provider, api_key, system_prompt, reduce_prompt, model_name)

def generate_keywords(text, provider, api_key, model_name=None, num_keywords=15):
    """
    Extracts the most relevant keywords/phrases from the document.
    """
    # For keywords, we can run on the first chunk or combined summaries if too large.
    # We will use the first 100k characters for keyword extraction.
    sample_text = text[:100000]
    
    system_prompt = (
        f"You are a professional indexer. Extract exactly {num_keywords} of the most important keywords, technical terms, "
        "or core concepts from the text. Return them as a JSON object with a single key 'keywords' containing a list of strings. "
        "Return ONLY the valid JSON, no markdown formatting blocks, no extra text."
    )
    
    user_prompt = f"Document content:\n\n{sample_text}"
    
    response = call_llm(provider, api_key, system_prompt, user_prompt, model_name, json_mode=True)
    
    # Parse JSON
    try:
        # Try to find JSON block if model wrapped it in markdown code block
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(response)
        return data.get("keywords", [])
    except Exception as e:
        # Fallback parse if it returned text instead of clean JSON
        # Split by comma or newline
        lines = [line.strip("- *0123456789. ") for line in response.strip().split("\n")]
        keywords = [k for k in lines if k and len(k) < 50][:num_keywords]
        return keywords

def generate_flashcards(text, provider, api_key, model_name=None):
    """
    Generates study flashcards (Front/Back questions/concepts).
    """
    sample_text = text[:80000] # Use up to ~80k characters
    
    system_prompt = (
        "You are an academic study assistant. Generate exactly 10 study flashcards from the text. "
        "Each flashcard must contain a 'front' (question, concept, or term) and a 'back' (answer, explanation, or definition). "
        "Return the result as a JSON object in this format:\n"
        "{\n"
        "  \"flashcards\": [\n"
        "    {\"front\": \"Question or Term 1\", \"back\": \"Answer or Explanation 1\"},\n"
        "    ...\n"
        "  ]\n"
        "}\n"
        "Ensure the definitions are concise and help with active recall. Return ONLY the valid JSON."
    )
    
    user_prompt = f"Document content:\n\n{sample_text}"
    
    response = call_llm(provider, api_key, system_prompt, user_prompt, model_name, json_mode=True)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(response)
        return data.get("flashcards", [])
    except Exception:
        # Fallback dummy list
        return [
            {"front": "Flashcard generation error", "back": "Could not parse JSON. Check API logs."}
        ]

def generate_quiz(text, provider, api_key, model_name=None, num_questions=5):
    """
    Generates a multiple choice quiz based on the document.
    """
    if num_questions <= 0:
        return []
        
    sample_text = text[:80000]
    
    system_prompt = (
        f"You are an educational designer. Generate exactly {num_questions} unique multiple choice questions (MCQs) to test comprehension of the text. "
        "For each question, provide 4 options (A, B, C, D), the correct option letter, and a brief explanation of why it is correct. "
        "Return the result as a JSON object in this format:\n"
        "{\n"
        "  \"quiz\": [\n"
        "    {\n"
        "      \"question\": \"Question text?\",\n"
        "      \"options\": {\"A\": \"Option A text\", \"B\": \"Option B text\", \"C\": \"Option C text\", \"D\": \"Option D text\"},\n"
        "      \"answer\": \"A\",\n"
        "      \"explanation\": \"Brief explanation...\"\n"
        "    },\n"
        "    ...\n"
        "  ]\n"
        "}\n"
        "Return ONLY the valid JSON."
    )
    
    user_prompt = f"Document content:\n\n{sample_text}"
    
    response = call_llm(provider, api_key, system_prompt, user_prompt, model_name, json_mode=True)
    
    try:
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            data = json.loads(response)
        return data.get("quiz", [])
    except Exception:
        # Fallback dummy list
        return [
            {
                "question": "Quiz generation error",
                "options": {"A": "Error", "B": "Error", "C": "Error", "D": "Error"},
                "answer": "A",
                "explanation": "Could not parse JSON. Check API logs."
            }
        ]
