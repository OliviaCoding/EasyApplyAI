import streamlit as st
import re
from datetime import datetime
from functools import lru_cache
from openai import OpenAI

# Utility function to create safe filenames
def sanitize_filename(text, default="file"):
    """
    Generate filesystem-safe filenames by:
    1. Extracting first line as name part
    2. Replacing special chars with underscores
    3. Adding timestamp for uniqueness
    """
    name_part = text.split('\n')[0].strip() if text else default
    safe_name = re.sub(r'[^\w-]', '_', name_part)[:50]  # Truncate to 50 chars
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{safe_name}_{timestamp}"

# Configure Streamlit page settings
st.set_page_config(page_title="AI Resume Generator", layout="wide")
st.title("📄 AI Resume Generator")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

@lru_cache(maxsize=32)  # Cache to avoid duplicate API calls
def generate_resume(info, job_desc):
    """
    Generate LaTeX resume content using OpenAI API
    Returns: Generated LaTeX content or None if failed
    """
    prompt = f"""
    Create a professional resume in LaTeX format based on:
    
    ---CANDIDATE INFORMATION---
    {info}
    
    ---TARGET JOB DESCRIPTION---
    {job_desc}
    
    Format requirements:
    1. Use \documentclass[11pt,a4paper]{{article}}
    2. Include sections: Header, Education, Experience, Skills
    3. Use hidelinks for hyperref
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
        
    except openai.APIConnectionError as e:
        st.error(f"API connection failed: {e.__cause__}")
    except openai.RateLimitError:
        st.error("Rate limit exceeded. Please wait...")
    except openai.APIError as e:
        st.error(f"API error: {e}")
    
    return None

def generate_cover_letter(info, job_desc):
    """
    Generate tailored cover letter using OpenAI API
    Returns: Generated text or None if failed
    """
    prompt = f"""
    Write professional cover letter based on:
    
    ---CANDIDATE PROFILE---
    {info}
    
    ---POSITION DETAILS---
    {job_desc}
    
    Requirements:
    1. 3-4 paragraphs
    2. Highlight relevant skills
    3. Professional tone
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=1000
        )
        return response.choices[0].message.content
        
    except Exception as e:
        st.error(f"Generation failed: {str(e)}")
        return None

# Main UI Layout
with st.expander("🔍 Enter Your Information", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        user_info = st.text_area(
            "Your Professional Details", 
            height=200,
            help="Include: Name, Education, Work Experience, Skills"
        )
    with col2:
        job_desc = st.text_area(
            "Target Job Description", 
            height=200,
            help="Paste the job posting or position requirements"
        )

# Generation Controls
generate_col1, generate_col2 = st.columns(2)
with generate_col1:
    resume_btn = st.button("Generate Resume (LaTeX)")
with generate_col2:
    cover_btn = st.button("Generate Cover Letter")

# Results Display
if resume_btn or cover_btn:
    if not user_info or not job_desc:
        st.warning("Please complete all fields")
    else:
        with st.spinner("Generating content..."):
            try:
                if resume_btn:
                    latex_resume = generate_resume(user_info, job_desc)
                    if latex_resume:
                        with st.container():
                            st.subheader("Generated LaTeX Resume")
                            st.code(latex_resume, language="latex")
                            
                            # Safe download button
                            dl_name = f"resume_{sanitize_filename(user_info, 'resume')}.tex"
                            st.download_button(
                                label="Download LaTeX File",
                                data=latex_resume,
                                file_name=dl_name,
                                mime="text/plain",
                                help="Filename includes your name and timestamp"
                            )
                
                if cover_btn:
                    cover_letter = generate_cover_letter(user_info, job_desc)
                    if cover_letter:
                        with st.container():
                            st.subheader("Generated Cover Letter")
                            st.text_area("Content Preview", cover_letter, height=400)
                            
                            # Safe download button
                            dl_name = f"cover_letter_{sanitize_filename(user_info, 'cover')}.txt"
                            st.download_button(
                                label="Download Cover Letter",
                                data=cover_letter,
                                file_name=dl_name,
                                mime="text/plain",
                                help="Filename includes your name and timestamp"
                            )
                            
            except Exception as e:
                st.error("System error during generation")
                st.exception(e)  # Detailed error for debugging

# Application Guide
st.sidebar.markdown("""
## User Guide
1. Fill in professional details
2. Paste job description
3. Click generation buttons
4. Download results

🔧 **Pro Tip**: 
- Use bullet points in experience section
- Include metrics (e.g. "Improved performance by 30%")
""")