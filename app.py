import streamlit as st
import re
from datetime import datetime
from openai import OpenAI
from weasyprint import HTML
import os
import PyPDF2
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
import ast
import json

# Utility function to create safe filenames
def sanitize_filename(text, default="file"):
    """Convert text to a safe filename by removing special chars and adding timestamp"""
    name_part = text.split('\n')[0].strip() if text else default
    safe_name = re.sub(r'[^\w-]', '_', name_part)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{safe_name}_{timestamp}"

# Configure Streamlit page settings
st.set_page_config(page_title="AI Resume Generator", layout="wide")
st.title("📄 Professional Resume & Cover Letter Generator")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Function to load template files
def load_template(template_name):
    """Load HTML templates from templates directory"""
    template_path = os.path.join('templates', template_name)
    with open(template_path, 'r', encoding='utf-8') as file:
        return file.read()

# Load templates at startup
RESUME_TEMPLATE = load_template('resume_template.html')
COVER_LETTER_TEMPLATE = load_template('cover_letter_template.html')

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF using PyPDF2, fallback to OCR if needed"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        pdf_file.seek(0)  # Reset file pointer
        
        # First try PyPDF2 text extraction
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        # Fallback to OCR if no text extracted
        if not text.strip():
            st.warning("No text extracted with PyPDF2. Attempting OCR...")
            images = convert_from_bytes(pdf_file.read())
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
        
        if not text.strip():
            st.error("Failed to extract text even with OCR.")
            return None
        
        # Fix common OCR errors
        text = text.replace("aqmail", "@").replace("spainish", "Spanish")
        
        with st.expander("Debug: Extracted PDF Text", expanded=False):
            st.text_area("Raw Extracted Text", text, height=200)
        
        return text
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def safe_literal_eval(s):
    """Safely evaluate string containing Python literal with automatic repair"""
    try:
        s = s.strip()
        
        # Fix common formatting issues
        if not s.startswith('[') and not s.startswith('{'):
            s = f'[{s}]'  # Try to wrap as list
            
        # Ensure quotes are balanced
        if s.count('"') % 2 != 0:
            s = s.replace('"', "'")  # Standardize on single quotes
        if s.count("'") % 2 != 0:
            s += "'"  # Add missing quote
            
        # Ensure brackets are balanced
        if s.count('[') > s.count(']'):
            s += ']' * (s.count('[') - s.count(']'))
        if s.count('{') > s.count('}'):
            s += '}' * (s.count('{') - s.count('}'))
            
        return ast.literal_eval(s)
    except (SyntaxError, ValueError) as e:
        st.error(f"Failed to parse data: {e}\nRaw content: {s}")
        return []  # Return empty list as safe default

def ai_parse_resume(text):
    """Use AI to extract structured data from resume text"""
    prompt = f"""
    Extract resume details into a PROPERLY FORMATED JSON object.
    Follow these rules STRICTLY:
    1. All strings must be properly quoted
    2. All brackets must be properly closed
    3. All fields must be included even if empty
    4. Use double quotes for JSON compliance
    5. Escape any special characters
    
    Required fields: name, phone, email, university, degree, etc.
    
    Example VALID output:
    {{
        "name": "John Doe",
        "education": [
            {{
                "university": "ABC University",
                "degree": "B.S. Computer Science",
                "dates": "2018-2022"
            }}
        ]
    }}
    
    Text to parse:
    {text[:3000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={ "type": "json_object" }
        )
        raw = response.choices[0].message.content
        return json.loads(raw)
    except Exception as e:
        st.error(f"AI parsing failed: {str(e)}")
        return {}

def validate_parsed_data(data):
    """Ensure parsed data has correct structure with all required fields"""
    if not isinstance(data, dict):
        return {}
    
    # Ensure all required fields exist
    required_fields = ["name", "phone", "email", "university", "degree"]
    for field in required_fields:
        if field not in data:
            data[field] = ""
    
    # Ensure list fields are properly formatted
    list_fields = ["education", "work_experience", "projects"]
    for field in list_fields:
        if field not in data or not isinstance(data[field], list):
            data[field] = []
    
    return data

def parse_resume_with_ai(resume_text):
    """Parse resume text into structured sections using AI"""
    extracted_data = validate_parsed_data(ai_parse_resume(resume_text))
    if not extracted_data:
        return None
    
    # Format the parsed data into standardized structure
    result = []
    
    # Personal Information
    personal_info = [
        extracted_data.get("name", ""),
        extracted_data.get("phone", ""),
        extracted_data.get("email", ""),
        extracted_data.get("linkedin", ""),
        extracted_data.get("github", "")
    ]
    result.append(f"- Personal Information: {personal_info}")
    
    # Education - ensure at least one education entry exists
    educations = []
    if extracted_data.get("university"):
        educations.append([
            extracted_data.get("university", ""),
            extracted_data.get("degree", ""),
            extracted_data.get("education_dates", ""),
            extracted_data.get("gpa", ""),
            extracted_data.get("university_location", ""),
            extracted_data.get("education_bullets", "")
        ])
    result.append(f"- Education: {educations}")
    
    # Work Experience - ensure at least one work entry exists
    work_experiences = []
    if extracted_data.get("job1_title"):
        work_experiences.append([
            extracted_data.get("job1_title", ""),
            extracted_data.get("job1_company", ""),
            extracted_data.get("job1_dates", ""),
            extracted_data.get("job1_location", ""),
            extracted_data.get("job1_desc", "")
        ])
    if extracted_data.get("job2_title"):
        work_experiences.append([
            extracted_data.get("job2_title", ""),
            extracted_data.get("job2_company", ""),
            extracted_data.get("job2_dates", ""),
            extracted_data.get("job2_location", ""),
            extracted_data.get("job2_desc", "")
        ])
    result.append(f"- Work Experience: {work_experiences}")
    
    # Skills with proper formatting
    skills = extracted_data.get("skills_content", "")
    result.append(f"- Skills: {[skills] if skills else []}")
    
    # Projects - ensure at least one project exists
    projects = []
    if extracted_data.get("project1_name"):
        projects.append([
            extracted_data.get("project1_name", ""),
            extracted_data.get("project1_date", ""),
            extracted_data.get("project1_context", ""),
            extracted_data.get("project1_desc", "")
        ])
    if extracted_data.get("project2_name"):
        projects.append([
            extracted_data.get("project2_name", ""),
            extracted_data.get("project2_date", ""),
            extracted_data.get("project2_context", ""),
            extracted_data.get("project2_desc", "")
        ])
    result.append(f"- Projects: {projects}")
    
    return "\n".join(result)

def rank_experiences(experiences, job_desc, exp_type="Work Experience"):
    prompt = f"""
    Given the following {exp_type} entries and job description, rank them by relevance to the job's technical stack and requirements. Return a list of indices in descending order of relevance (most relevant first).

    {exp_type} Entries:
    {', '.join([f'{i}: {e}' for i, e in enumerate(experiences)])}

    Job Description:
    {job_desc}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500
        )
        indices = ast.literal_eval(response.choices[0].message.content)
        return indices
    except Exception as e:
        st.error(f"Failed to rank {exp_type}: {str(e)}")
        return list(range(len(experiences)))

def generate_bullet_points(prompt_text, max_bullets=3, job_desc=None):
    prompt = f"Convert this into {max_bullets} professional bullet points. Use strong action verbs and quantify results.\n"
    if job_desc:
        prompt += f"Tailor to this job description:\n{job_desc}\n\n"
    prompt += f"{prompt_text}\nReturn only bullet points, each on a new line."
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=300
        )
        bullets = response.choices[0].message.content.strip().split('\n')
        return "\n".join([f"<li>{b.strip('-• ')}</li>" for b in bullets[:max_bullets] if b.strip()])
    except Exception as e:
        st.error(f"Failed to generate bullet points: {str(e)}")
        return "<li>Error generating bullet points</li>"

def generate_pdf(html_content):
    try:
        html = HTML(string=html_content)
        return html.write_pdf()
    except Exception as e:
        st.error(f"PDF generation failed: {str(e)}")
        return None

# Initialize session state for dynamic entries
if 'educations' not in st.session_state:
    st.session_state['educations'] = []
if 'work_experiences' not in st.session_state:
    st.session_state['work_experiences'] = []
if 'projects' not in st.session_state:
    st.session_state['projects'] = []
if 'parsed' not in st.session_state:
    st.session_state['parsed'] = False

# Main form tabs
tab1, tab2 = st.tabs(["📝 Resume Builder", "✉️ Cover Letter Generator"])

with tab1:
    st.subheader("Resume Builder")

    # Upload resume option
    uploaded_file = st.file_uploader("Upload your existing resume (PDF)", type=["pdf"])
    if uploaded_file and not st.session_state['parsed']:
        with st.spinner("Parsing your resume..."):
            resume_text = extract_text_from_pdf(uploaded_file)
            if resume_text:
                parsed_data = parse_resume_with_ai(resume_text)
                if parsed_data:
                    lines = parsed_data.split('\n')
                    for line in lines:
                        if line.startswith("- Personal Information:"):
                            info = ast.literal_eval(line.split(":")[1].strip())
                            st.session_state['resume_name'] = info[0] if info[0] != 'N/A' else ""
                            st.session_state['resume_phone'] = info[1] if info[1] != 'N/A' else ""
                            st.session_state['resume_email'] = info[2] if info[2] != 'N/A' else ""
                            st.session_state['resume_linkedin'] = info[3] if info[3] != 'N/A' else ""
                            st.session_state['resume_github'] = info[4] if info[4] != 'N/A' else ""
                        elif line.startswith("- Education:"):
                            def safe_literal_eval(s):
                                try:
                                    # Ensure proper closing of brackets/quotes
                                    if s.count('[') > s.count(']'):
                                        s += ']' * (s.count('[') - s.count(']'))
                                    if s.count('"') % 2 != 0:
                                        s += '"'
                                    if s.count("'") % 2 != 0:
                                        s += "'"
                                    return ast.literal_eval(s)
                                except (SyntaxError, ValueError) as e:
                                    st.error(f"Failed to parse: {s}")
                                    return []

                            educations = safe_literal_eval(line.split(":")[1].strip())[:3]

                            st.session_state['educations'] = educations
                            for i, edu in enumerate(educations):
                                st.session_state[f"edu_university_{i}"] = edu[0] if edu[0] != 'N/A' else ""
                                st.session_state[f"edu_degree_{i}"] = edu[1] if edu[1] != 'N/A' else ""
                                st.session_state[f"edu_dates_{i}"] = edu[2] if edu[2] != 'N/A' else ""
                                st.session_state[f"edu_gpa_{i}"] = edu[3] if edu[3] != 'N/A' else ""
                                st.session_state[f"edu_location_{i}"] = edu[4] if edu[4] != 'N/A' else ""
                                st.session_state[f"edu_bullets_{i}"] = edu[5] if edu[5] != 'N/A' else ""
                        elif line.startswith("- Work Experience:"):
                            experiences = ast.literal_eval(line.split(":")[1].strip())[:10]
                            st.session_state['work_experiences'] = experiences
                            for i, exp in enumerate(experiences):
                                st.session_state[f"exp_title_{i}"] = exp[0] if exp[0] != 'N/A' else ""
                                st.session_state[f"exp_company_{i}"] = exp[1] if exp[1] != 'N/A' else ""
                                st.session_state[f"exp_dates_{i}"] = exp[2] if exp[2] != 'N/A' else ""
                                st.session_state[f"exp_location_{i}"] = exp[3] if exp[3] != 'N/A' else ""
                                st.session_state[f"exp_desc_{i}"] = exp[4] if exp[4] != 'N/A' else ""
                        elif line.startswith("- Skills:"):
                            skills = line.split(":")[1].strip()[1:-1]
                            st.session_state['resume_skills_content'] = skills if skills != 'N/A' else ""
                        elif line.startswith("- Projects:"):
                            projects = ast.literal_eval(line.split(":")[1].strip())[:10]
                            st.session_state['projects'] = projects
                            for i, proj in enumerate(projects):
                                st.session_state[f"proj_name_{i}"] = proj[0] if proj[0] != 'N/A' else ""
                                st.session_state[f"proj_date_{i}"] = proj[1] if proj[1] != 'N/A' else ""
                                st.session_state[f"proj_context_{i}"] = proj[2] if proj[2] != 'N/A' else ""
                                st.session_state[f"proj_desc_{i}"] = proj[3] if proj[3] != 'N/A' else ""
                    st.session_state['parsed'] = True
                    st.success("Resume parsed! Edit below as needed.")
                    st.rerun()  # Rerun to reflect parsed data in form

    # Job description
    job_desc = st.text_area("Paste Job Description*", height=200,
        help="Used to tailor your resume",
        placeholder="Paste the full job description here...",
        key="resume_job_desc")

    # Personal Information
    with st.expander("🔍 Personal Information", expanded=True):
        name = st.text_input("Full Name*", value=st.session_state.get('resume_name', ""), key="resume_name")
        col1, col2 = st.columns(2)
        with col1:
            phone = st.text_input("Phone Number*", value=st.session_state.get('resume_phone', ""), key="resume_phone")
            linkedin = st.text_input("LinkedIn URL", value=st.session_state.get('resume_linkedin', ""), key="resume_linkedin")
        with col2:
            email = st.text_input("Email*", value=st.session_state.get('resume_email', ""), key="resume_email")
            github = st.text_input("GitHub URL", value=st.session_state.get('resume_github', ""), key="resume_github")

    # Education
    with st.expander("🎓 Education"):
        for i, edu in enumerate(st.session_state['educations']):
            st.subheader(f"Education {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                university = st.text_input(f"University Name* ({i+1})", value=st.session_state.get(f"edu_university_{i}", edu[0]), key=f"edu_university_{i}")
                degree = st.text_input(f"Degree* ({i+1})", value=st.session_state.get(f"edu_degree_{i}", edu[1]), key=f"edu_degree_{i}")
            with col2:
                dates = st.text_input(f"Dates Attended* ({i+1})", value=st.session_state.get(f"edu_dates_{i}", edu[2]), key=f"edu_dates_{i}")
                gpa = st.text_input(f"GPA ({i+1})", value=st.session_state.get(f"edu_gpa_{i}", edu[3]), key=f"edu_gpa_{i}")
            location = st.text_input(f"Location* ({i+1})", value=st.session_state.get(f"edu_location_{i}", edu[4]), key=f"edu_location_{i}")
            bullets = st.text_area(f"Additional Details ({i+1})", value=st.session_state.get(f"edu_bullets_{i}", edu[5]), key=f"edu_bullets_{i}")
            if st.button(f"Delete Education {i+1}", key=f"delete_edu_{i}"):
                st.session_state['educations'].pop(i)
                for j in range(i, len(st.session_state['educations'])):
                    for field in ["university", "degree", "dates", "gpa", "location", "bullets"]:
                        st.session_state[f"edu_{field}_{j}"] = st.session_state.get(f"edu_{field}_{j+1}", "")
                st.rerun()
            st.session_state['educations'][i] = [university, degree, dates, gpa, location, bullets]
        if len(st.session_state['educations']) < 3:
            if st.button("Add Education"):
                st.session_state['educations'].append(["", "", "", "", "", ""])
                st.rerun()

    # Work Experience
    with st.expander("💼 Work Experience"):
        for i, exp in enumerate(st.session_state['work_experiences']):
            st.subheader(f"Work Experience {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input(f"Job Title* ({i+1})", value=st.session_state.get(f"exp_title_{i}", exp[0]), key=f"exp_title_{i}")
                company = st.text_input(f"Company Name* ({i+1})", value=st.session_state.get(f"exp_company_{i}", exp[1]), key=f"exp_company_{i}")
            with col2:
                dates = st.text_input(f"Dates* ({i+1})", value=st.session_state.get(f"exp_dates_{i}", exp[2]), key=f"exp_dates_{i}")
                location = st.text_input(f"Location* ({i+1})", value=st.session_state.get(f"exp_location_{i}", exp[3]), key=f"exp_location_{i}")
            desc = st.text_area(f"Description* ({i+1})", value=st.session_state.get(f"exp_desc_{i}", exp[4]), key=f"exp_desc_{i}")
            if st.button(f"Delete Work Experience {i+1}", key=f"delete_exp_{i}"):
                st.session_state['work_experiences'].pop(i)
                for j in range(i, len(st.session_state['work_experiences'])):
                    for field in ["title", "company", "dates", "location", "desc"]:
                        st.session_state[f"exp_{field}_{j}"] = st.session_state.get(f"exp_{field}_{j+1}", "")
                st.rerun()
            st.session_state['work_experiences'][i] = [title, company, dates, location, desc]
        if len(st.session_state['work_experiences']) < 10:
            if st.button("Add Work Experience"):
                st.session_state['work_experiences'].append(["", "", "", "", ""])
                st.rerun()

    # Skills
    with st.expander("🛠 Skills"):
        skills_content = st.text_area("Technical Skills*", height=100,
            value=st.session_state.get('resume_skills_content', ""),
            help="Format: Languages: Java, Python | Technologies: React",
            key="resume_skills_content")

    # Projects
    with st.expander("🚀 Projects"):
        for i, proj in enumerate(st.session_state['projects']):
            st.subheader(f"Project {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"Project Name ({i+1})", value=st.session_state.get(f"proj_name_{i}", proj[0]), key=f"proj_name_{i}")
                date = st.text_input(f"Completion Date ({i+1})", value=st.session_state.get(f"proj_date_{i}", proj[1]), key=f"proj_date_{i}")
            with col2:
                context = st.text_input(f"Context ({i+1})", value=st.session_state.get(f"proj_context_{i}", proj[2]), key=f"proj_context_{i}")
            desc = st.text_area(f"Description ({i+1})", value=st.session_state.get(f"proj_desc_{i}", proj[3]), key=f"proj_desc_{i}")
            if st.button(f"Delete Project {i+1}", key=f"delete_proj_{i}"):
                st.session_state['projects'].pop(i)
                for j in range(i, len(st.session_state['projects'])):
                    for field in ["name", "date", "context", "desc"]:
                        st.session_state[f"proj_{field}_{j}"] = st.session_state.get(f"proj_{field}_{j+1}", "")
                st.rerun()
            st.session_state['projects'][i] = [name, date, context, desc]
        if len(st.session_state['projects']) < 10:
            if st.button("Add Project"):
                st.session_state['projects'].append(["", "", "", ""])
                st.rerun()

    # Selection for final resume
    st.subheader("Select Experiences for Final Resume (Max 4 Total)")
    selection_method = st.radio("Selection Method", ("Manual Selection", "AI Auto-Select"))
    
    selected_experiences = []
    if selection_method == "Manual Selection":
        for i, exp in enumerate(st.session_state['work_experiences']):
            if st.checkbox(f"Work: {exp[0]} at {exp[1]} ({exp[2]})", key=f"select_exp_{i}"):
                selected_experiences.append(("work", i))
        for i, proj in enumerate(st.session_state['projects']):
            if st.checkbox(f"Project: {proj[0]} ({proj[1]})", key=f"select_proj_{i}"):
                selected_experiences.append(("project", i))
        if len(selected_experiences) > 4:
            st.warning("Please select up to 4 experiences total.")
    elif selection_method == "AI Auto-Select" and job_desc:
        work_indices = rank_experiences(st.session_state['work_experiences'], job_desc, "Work Experience")
        proj_indices = rank_experiences(st.session_state['projects'], job_desc, "Projects")
        combined = [(("work", i) for i in work_indices)] + [(("project", i) for i in proj_indices)]
        selected_experiences = combined[:4]

    # Generate Resume Button
    if st.button("✨ Generate Tailored Resume", type="primary", key="generate_resume_btn"):
        if not name or not st.session_state['educations'] or not job_desc:
            st.error("Please fill in required fields and add at least one education entry.")
        elif selection_method == "Manual Selection" and len(selected_experiences) > 4:
            st.error("Please select up to 4 experiences.")
        else:
            with st.spinner("Generating your tailored resume..."):
                try:
                    # Use first education entry for resume (1-page limit)
                    edu = st.session_state['educations'][0]
                    edu_bullets = "\n".join([f"<li>{line.strip()}</li>" for line in edu[5].split('\n') if line.strip()][:3]) if edu[5] else ""

                    # Prepare selected experiences
                    final_work = []
                    final_projects = []
                    for exp_type, idx in selected_experiences[:4]:
                        if exp_type == "work":
                            final_work.append(st.session_state['work_experiences'][idx])
                        elif exp_type == "project":
                            final_projects.append(st.session_state['projects'][idx])
                    while len(final_work) < 2:
                        final_work.append(["Position", "Company", "Dates", "Location", ""])
                    while len(final_projects) < 2:
                        final_projects.append(["Project Name", "Date", "Context", ""])

                    # Generate bullet points
                    job1_bullets = generate_bullet_points(final_work[0][4], max_bullets=3, job_desc=job_desc)
                    job2_bullets = generate_bullet_points(final_work[1][4], max_bullets=2, job_desc=job_desc)
                    project1_bullets = generate_bullet_points(final_projects[0][3], max_bullets=2, job_desc=job_desc)
                    project2_bullets = generate_bullet_points(final_projects[1][3], max_bullets=2, job_desc=job_desc)

                    # Format skills
                    skills_formatted = "\n".join([
                        f'<div class="skill-category"><strong>{cat.split(":")[0].strip()}:</strong>{cat.split(":")[1].strip()}</div>'
                        for cat in skills_content.split("\n") if ":" in cat
                    ]) if skills_content else '<div class="skill-category"><strong>Languages:</strong> Python, Java</div>'

                    # Format contact links
                    linkedin_html = f'<a href="{linkedin}">LinkedIn</a>' if linkedin else "LinkedIn: Not provided"
                    github_html = f'<a href="{github}">GitHub</a>' if github else "GitHub: Not provided"

                    # Generate HTML resume
                    html_resume = RESUME_TEMPLATE.format(
                        name=name,
                        phone=phone,
                        email=email,
                        linkedin_html=linkedin_html,
                        github_html=github_html,
                        university=edu[0],
                        education_dates=edu[2],
                        degree=edu[1],
                        gpa=f" | <strong>GPA:</strong> {edu[3]}" if edu[3] else "",
                        university_location=edu[4],
                        education_bullets=edu_bullets,
                        skills_content=skills_formatted,
                        job1_title=final_work[0][0],
                        job1_dates=final_work[0][2],
                        job1_company=final_work[0][1],
                        job1_location=final_work[0][3],
                        job1_bullets=job1_bullets,
                        job2_title=final_work[1][0],
                        job2_dates=final_work[1][2],
                        job2_company=final_work[1][1],
                        job2_location=final_work[1][3],
                        job2_bullets=job2_bullets,
                        project1_name=final_projects[0][0],
                        project1_context=final_projects[0][2],
                        project1_date=final_projects[0][1],
                        project1_bullets=project1_bullets,
                        project2_name=final_projects[1][0],
                        project2_context=final_projects[1][2],
                        project2_date=final_projects[1][1],
                        project2_bullets=project2_bullets,
                    )

                    # Generate PDF
                    pdf_bytes = generate_pdf(html_resume)

                    # Display and download options
                    st.subheader("Your Tailored Resume")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button(
                            label="📥 Download PDF",
                            data=pdf_bytes,
                            file_name=f"resume_{sanitize_filename(name)}.pdf",
                            mime="application/pdf"
                        )
                    with col2:
                        st.download_button(
                            label="📄 Download HTML",
                            data=html_resume,
                            file_name=f"resume_{sanitize_filename(name)}.html",
                            mime="text/html"
                        )
                    st.components.v1.html(html_resume, height=800, scrolling=True)

                except Exception as e:
                    st.error("Error generating resume")
                    st.exception(e)

with tab2:
    st.subheader("Cover Letter Generator")
    job_desc = st.text_area("Paste Job Description*", height=200,
        help="Copy and paste the job posting you're applying for",
        placeholder="Paste the full job description here...")
    
    with st.expander("✉️ Cover Letter Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            hiring_manager = st.text_input("Hiring Manager Name (if known)", placeholder="John Smith")
            company_name = st.text_input("Company Name*", placeholder="Tech Innovations Inc.")
            company_address = st.text_input("Company Street Address", placeholder="123 Main Street")
        with col2:
            job_title = st.text_input("Job Title*", placeholder="Senior Software Engineer")
            your_name = st.text_input("Your Name*", value=st.session_state.get("resume_name", ""))
            company_city_state_zip = st.text_input("City, State ZIP Code", placeholder="New York, NY 10001")

    if st.button("✍️ Generate Cover Letter", type="primary", key="generate_cover_letter_btn"):
        if not job_desc or not company_name or not job_title or not your_name:
            st.error("Please fill in all required fields (marked with *)")
        else:
            with st.spinner("Generating your tailored cover letter..."):
                try:
                    user_email = st.session_state.get("resume_email", "[Email]")
                    candidate_info = f"""
                    Candidate Name: {your_name}
                    Education:
                    - {st.session_state['educations'][0][1] if st.session_state['educations'] else ''} at {st.session_state['educations'][0][0] if st.session_state['educations'] else ''}
                    Work Experience:
                    - {st.session_state['work_experiences'][0][0] if st.session_state['work_experiences'] else ''} at {st.session_state['work_experiences'][0][1] if st.session_state['work_experiences'] else ''}
                    Skills:
                    {st.session_state.get("resume_skills_content", "")}
                    """
                    cover_letter_content = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": f"""
                            Write a cover letter body (3-4 paragraphs) based on:
                            ---CANDIDATE PROFILE---
                            {candidate_info}
                            ---JOB DESCRIPTION---
                            {job_desc}
                            Focus on matching skills to job requirements, keep it concise (200-300 words).
                            Return only the body content.
                        """}],
                        temperature=0.5,
                        max_tokens=1000
                    ).choices[0].message.content
                    formatted_letter = f"""
{datetime.now().strftime("%B %d, %Y")}

{hiring_manager if hiring_manager else "Hiring Manager"}
{company_name}
{company_address if company_address else ""}
{company_city_state_zip if company_city_state_zip else ""}

{'Dear ' + hiring_manager + ',' if hiring_manager else 'Dear Hiring Manager,'}

{cover_letter_content}

Sincerely,
{your_name}
"""
                    st.session_state['formatted_letter'] = formatted_letter
                    st.session_state['cover_letter_content'] = cover_letter_content
                    st.session_state['cover_letter_generated'] = True
                    html_letter = COVER_LETTER_TEMPLATE.format(
                        name=your_name,
                        date=datetime.now().strftime("%B %d, %Y"),
                        recipient_name=hiring_manager if hiring_manager else "Hiring Manager",
                        company_name=company_name,
                        company_address=company_address if company_address else "",
                        company_city_state_zip=company_city_state_zip if company_city_state_zip else "",
                        salutation=f"Dear {hiring_manager}," if hiring_manager else "Dear Hiring Manager,",
                        content=cover_letter_content
                    )
                    st.session_state['html_letter'] = html_letter

                except Exception as e:
                    st.error("Error generating cover letter")
                    st.exception(e)

    if st.session_state.get('cover_letter_generated', False):
        st.subheader("Your Tailored Cover Letter")
        st.text_area("Preview", st.session_state['formatted_letter'], height=500, key="cover_letter_preview")
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📥 Download as TXT",
                data=st.session_state['formatted_letter'],
                file_name=f"cover_letter_{sanitize_filename(job_title)}.txt",
                mime="text/plain",
                key="download_txt"
            )
        with col2:
            st.download_button(
                label="📄 Download as PDF",
                data=generate_pdf(st.session_state['html_letter']),
                file_name=f"cover_letter_{sanitize_filename(job_title)}.pdf",
                mime="application/pdf",
                key="download_pdf"
            )

# Instructions
st.sidebar.markdown("""
## 📝 Instructions
**Resume Builder:**
1. Upload a resume (optional) or add entries manually
2. Edit/add up to 3 Educations, 10 Work Experiences, 10 Projects
3. Paste job description to tailor resume
4. Select up to 4 experiences (manual or AI)
5. Generate and download resume

**Cover Letter Generator:**
1. Paste job description
2. Fill in company details
3. Generate and download cover letter

## 💡 Tips
- Quantify achievements
- Keep bullets concise
- Tailor to job description
""")