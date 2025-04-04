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
import json

# Ensure session state key exists
if 'html_letter' not in st.session_state:
    st.session_state['html_letter'] = ""

# Utility function to create safe filenames
def sanitize_filename(text, default="file"):
    name_part = text.split('\n')[0].strip() if text else default
    safe_name = re.sub(r'[^\w-]', '_', name_part)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{safe_name}_{timestamp}"

# Configure Streamlit page settings
st.set_page_config(page_title="AI Resume Generator", layout="wide")
st.title("📄 Professional Resume & Cover Letter Generator")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def load_template(template_name):
    template_path = os.path.join('templates', template_name)
    try:
        with open(template_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        st.error(f"Template {template_name} not found.")
        return "<html><body>Error: Template not found</body></html>"

# Load templates at startup
RESUME_TEMPLATE = load_template('resume_template.html')
COVER_LETTER_TEMPLATE = load_template('cover_letter_template.html')

# if not st.session_state['html_letter']:
#     st.session_state['html_letter'] = COVER_LETTER_TEMPLATE.format(
#         date=datetime.now().strftime("%B %d, %Y"),
#         name="Your Name",
#         recipient_name="Hiring Manager",
#         company_name="",
#         company_address="",
#         company_city_state_zip="",
#         salutation="Dear Hiring Manager,",
#         content=""
#     )

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        pdf_file.seek(0)
        
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        if not text.strip():
            st.warning("No text extracted with PyPDF2. Attempting OCR...")
            images = convert_from_bytes(pdf_file.read())
            for image in images:
                text += pytesseract.image_to_string(image) + "\n"
        
        if not text.strip():
            st.error("Failed to extract text even with OCR.")
            return None
        
        text = text.replace("aqmail", "@").replace("spainish", "Spanish")
        
        with st.expander("Debug: Extracted PDF Text", expanded=True):
            st.text_area("Raw Extracted Text", text, height=200)
        
        extracted_data = ai_parse_resume(text)
        
        with st.expander("Debug: Extracted Data", expanded=False):
            st.json(extracted_data)
        
        return extracted_data
    
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def ai_parse_resume(text):
    prompt = f"""
    Extract resume data with strict validation. Follow these rules:

    1. NAME:
       - Likely at the top (first 10 lines)
       - Format: FirstName LastName, FirstName M. LastName, or similar
       - Often near contact info (phone/email)
       - NOT matching project/company names
       - NOT all uppercase/lowercase unless clearly a name
       - Example: "John Doe", "Jane M. Smith"

    2. IGNORE AS NAMES:
       - PicSpeaks, AI Agent, LaGuardia, or standalone uppercase words not near contact info

    3. IF NAME UNSURE:
       - Return best guess or empty string

    4. WORK EXPERIENCE (CRITICAL):
       - Identify under headers: "Work Experience," "Experience," "Employment," "Professional Experience," "Job History"
       - Detect entries with job titles followed by dates, company, and optionally location/description
       - Extract:
         - "title": Job title
         - "company": Company name
         - "dates": Date range (e.g., "July 2023 - Aug. 2023")
         - "location": City/State (if present)
         - "description": Details or bullets (combine into one string)
       - Examples:
         - "Web Development Intern\nJuly 2023 - Aug. 2023\nLaGuardia Community College IT Department\nLong Island City, NY\n- Designed and built webpage"
         - "Software Engineer, Tech Corp, Jan 2020 - Dec 2022, New York - Developed apps"
       - Be flexible with multi-line or inline formats

    5. PROJECTS:
       - Identify under "Projects," "Personal Projects," or similar
       - Use "project_name" as title key
       - Include "date," "context," "description" (optional)

    6. LINKEDIN/GITHUB:
       - Extract URLs with "linkedin.com" or "github.com" near contact info or elsewhere

    Return JSON:
    {{
        "name": "string",
        "phone": "string",
        "email": "string",
        "linkedin": "string",
        "github": "string",
        "projects": [
            {{
                "project_name": "string",
                "date": "string",
                "context": "string",
                "description": "string"
            }}
        ],
        "educations": [
            {{
                "university": "string",
                "degree": "string",
                "dates": "string",
                "gpa": "string",
                "location": "string",
                "bullets": "string"
            }}
        ],
        "work_experiences": [
            {{
                "title": "string",
                "company": "string",
                "dates": "string",
                "location": "string",
                "description": "string"
            }}
        ],
        "skills": "string"
    }}

    Resume text:
    {text[:4000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1500
        )
        response_content = response.choices[0].message.content
        data = json.loads(response_content)
        
        project_names = [p.get("project_name", "").lower() for p in data.get("projects", [])]
        if data.get("name", "").lower() in project_names:
            data["name"] = ""
            st.warning("Personal name matched a project name - reset to empty")
        
        with st.expander("Debug: AI Parsed Output", expanded=True):
            st.json(data)
            if not data.get("work_experiences"):
                st.warning("No work experiences detected. Check resume format.")
        
        return data
    except Exception as e:
        st.error(f"AI parsing failed with error: {str(e)}")
        st.exception(e)
        return {"name": "", "phone": "", "email": "", "linkedin": "", "github": "", "projects": [], "educations": [], "work_experiences": [], "skills": ""}

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

def rank_experiences(experiences, job_desc, exp_type="Work Experience"):
    if not experiences or not job_desc:
        return list(range(len(experiences)))
    
    prompt = f"""
    Rank the following {exp_type} entries by relevance to the job description’s technical stack and requirements.
    Return ONLY a JSON list of indices in descending order of relevance (most relevant first).
    Do NOT include explanations or additional text outside the JSON list.

    {exp_type} Entries:
    {json.dumps([{i: str(e)} for i, e in enumerate(experiences)], indent=2)}

    Job Description:
    {job_desc}

    Example output:
    [1, 0, 2]
    """
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=500
        )
        response_content = response.choices[0].message.content.strip()
        indices = json.loads(response_content)
        if not isinstance(indices, list):
            raise ValueError(f"Response is not a list: {response_content}")
        valid_indices = [i for i in indices if i < len(experiences)]
        if not valid_indices:
            st.warning(f"No valid {exp_type} indices returned. Using default order.")
            return list(range(len(experiences)))
        return valid_indices
    except Exception as e:
        st.error(f"Failed to rank {exp_type}: {str(e)}")
        st.write(f"Raw AI response: {response_content if 'response_content' in locals() else 'No response'}")
        return list(range(len(experiences)))

# Initialize session state
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

    uploaded_file = st.file_uploader("Upload your existing resume (PDF)", type=["pdf"])
    if uploaded_file and not st.session_state['parsed']:
        with st.spinner("Parsing your resume..."):
            extracted_data = extract_text_from_pdf(uploaded_file)
            if extracted_data:
                st.session_state['resume_name'] = extracted_data.get("name", "")
                st.session_state['resume_phone'] = extracted_data.get("phone", "")
                st.session_state['resume_email'] = extracted_data.get("email", "")
                st.session_state['resume_linkedin'] = extracted_data.get("linkedin", "")
                st.session_state['resume_github'] = extracted_data.get("github", "")
                
                st.session_state['educations'] = [
                    [
                        edu.get("university", ""),
                        edu.get("degree", ""),
                        edu.get("dates", ""),
                        edu.get("gpa", ""),
                        edu.get("location", ""),
                        "\n".join([f"<li>{line.strip()}</li>" for line in edu.get("bullets", "").split('\n') if line.strip()])
                    ] for edu in extracted_data.get("educations", [])
                ]
                
                st.session_state['work_experiences'] = [
                    [
                        exp.get("title", ""),
                        exp.get("company", ""),
                        exp.get("dates", ""),
                        exp.get("location", ""),
                        exp.get("description", "")
                    ] for exp in extracted_data.get("work_experiences", [])
                ]
                
                st.session_state['projects'] = [
                    [
                        proj.get("project_name", ""),
                        proj.get("date", ""),
                        proj.get("context", ""),
                        proj.get("description", "")
                    ] for proj in extracted_data.get("projects", [])
                ]
                
                st.session_state['resume_skills_content'] = extracted_data.get("skills", "").strip()
                
                st.session_state['parsed'] = True
                st.success("Resume parsed! Edit below as needed.")
                st.rerun()

    job_desc = st.text_area("Paste Job Description*", height=200,
                           help="Used to tailor your resume",
                           placeholder="Paste the full job description here...",
                           key="resume_job_desc")

    with st.expander("🔍 Personal Information", expanded=True):
        if 'resume_name' not in st.session_state:
            st.session_state['resume_name'] = ""
        name = st.text_input("Full Name*", key="resume_name")
        
        col1, col2 = st.columns(2)
        with col1:
            if 'resume_phone' not in st.session_state:
                st.session_state['resume_phone'] = ""
            phone = st.text_input("Phone Number*", key="resume_phone")
            if 'resume_linkedin' not in st.session_state:
                st.session_state['resume_linkedin'] = ""
            linkedin = st.text_input("LinkedIn URL", key="resume_linkedin")
        with col2:
            if 'resume_email' not in st.session_state:
                st.session_state['resume_email'] = ""
            email = st.text_input("Email*", key="resume_email")
            if 'resume_github' not in st.session_state:
                st.session_state['resume_github'] = ""
            github = st.text_input("GitHub URL", key="resume_github")

    with st.expander("🎓 Education"):
        for i, edu in enumerate(st.session_state['educations']):
            st.subheader(f"Education {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                university = st.text_input(f"University Name* ({i+1})", value=edu[0], key=f"edu_university_{i}")
                degree = st.text_input(f"Degree* ({i+1})", value=edu[1], key=f"edu_degree_{i}")
            with col2:
                dates = st.text_input(f"Dates Attended* ({i+1})", value=edu[2], key=f"edu_dates_{i}")
                gpa = st.text_input(f"GPA ({i+1})", value=edu[3], key=f"edu_gpa_{i}")
            location = st.text_input(f"Location* ({i+1})", value=edu[4], key=f"edu_location_{i}")
            bullets_display = re.sub(r'<[^>]+>', '', edu[5]).strip()
            bullets = st.text_area(f"Additional Details ({i+1})", value=bullets_display, key=f"edu_bullets_{i}")
            
            if st.button(f"Delete Education {i+1}", key=f"delete_edu_{i}"):
                st.session_state['educations'].pop(i)
                st.rerun()
            
            st.session_state['educations'][i] = [university, degree, dates, gpa, location, "\n".join([f"<li>{line.strip()}</li>" for line in bullets.split('\n') if line.strip()])]
        
        if len(st.session_state['educations']) < 3 and st.button("Add Education"):
            st.session_state['educations'].append(["", "", "", "", "", ""])
            st.rerun()

    with st.expander("💼 Work Experience"):
        for i, exp in enumerate(st.session_state['work_experiences']):
            st.subheader(f"Work Experience {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                title = st.text_input(f"Job Title* ({i+1})", value=exp[0], key=f"exp_title_{i}")
                company = st.text_input(f"Company Name* ({i+1})", value=exp[1], key=f"exp_company_{i}")
            with col2:
                dates = st.text_input(f"Dates* ({i+1})", value=exp[2], key=f"exp_dates_{i}")
                location = st.text_input(f"Location* ({i+1})", value=exp[3], key=f"exp_location_{i}")
            desc = st.text_area(f"Description* ({i+1})", value=exp[4], key=f"exp_desc_{i}")
            
            if st.button(f"Delete Work Experience {i+1}", key=f"delete_exp_{i}"):
                st.session_state['work_experiences'].pop(i)
                st.rerun()
            
            st.session_state['work_experiences'][i] = [title, company, dates, location, desc]
        
        if len(st.session_state['work_experiences']) < 10 and st.button("Add Work Experience"):
            st.session_state['work_experiences'].append(["", "", "", "", ""])
            st.rerun()

    with st.expander("🛠 Skills"):
        skills_content = st.text_area("Technical Skills*", height=100,
                                      value=st.session_state.get('resume_skills_content', ""),
                                      help="Format: Languages: Java, Python | Technologies: React",
                                      key="resume_skills_content")

    with st.expander("🚀 Projects"):
        for i, proj in enumerate(st.session_state['projects']):
            st.subheader(f"Project {i+1}")
            col1, col2 = st.columns(2)
            with col1:
                proj_name = st.text_input(f"Project Name ({i+1})", value=proj[0], key=f"proj_name_{i}")
                date = st.text_input(f"Completion Date ({i+1})", value=proj[1], key=f"proj_date_{i}")
            with col2:
                context = st.text_input(f"Context ({i+1})", value=proj[2], key=f"proj_context_{i}")
            desc_display = re.sub(r'<[^>]+>', '', proj[3]).strip()
            desc = st.text_area(f"Description ({i+1})", value=desc_display, key=f"proj_desc_{i}")
            
            if st.button(f"Delete Project {i+1}", key=f"delete_proj_{i}"):
                st.session_state['projects'].pop(i)
                st.rerun()
            
            st.session_state['projects'][i] = [proj_name, date, context, "\n".join([f"<li>{line.strip()}</li>" for line in desc.split('\n') if line.strip()])]
        
        if len(st.session_state['projects']) < 10 and st.button("Add Project"):
            st.session_state['projects'].append(["", "", "", ""])
            st.rerun()

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
        selected_experiences = [("work", i) for i in work_indices[:4]] + [("project", i) for i in proj_indices[:4]]
        selected_experiences = selected_experiences[:4]

    if st.button("✨ Generate Tailored Resume", type="primary", key="generate_resume_btn"):
        if not name or not st.session_state['educations'] or not job_desc:
            st.error("Please fill in required fields and add at least one education entry.")
        elif selection_method == "Manual Selection" and len(selected_experiences) > 4:
            st.error("Please select up to 4 experiences.")
        else:
            with st.spinner("Generating your tailored resume..."):
                try:
                    edu = st.session_state['educations'][0]
                    edu_bullets = edu[5] if edu[5] else "<li>Degree in progress</li>"
                    
                    final_work = []
                    final_projects = []
                    for exp_type, idx in selected_experiences[:4]:
                        if exp_type == "work":
                            final_work.append(st.session_state['work_experiences'][idx])
                        elif exp_type == "project":
                            final_projects.append(st.session_state['projects'][idx])
                    
                    job1_bullets = generate_bullet_points(final_work[0][4], max_bullets=3, job_desc=job_desc) if final_work else ""
                    job2_bullets = generate_bullet_points(final_work[1][4], max_bullets=2, job_desc=job_desc) if len(final_work) > 1 else ""
                    project1_bullets = generate_bullet_points(final_projects[0][3], max_bullets=2, job_desc=job_desc) if final_projects else ""
                    project2_bullets = generate_bullet_points(final_projects[1][3], max_bullets=2, job_desc=job_desc) if len(final_projects) > 1 else ""
                    
                    skills_formatted = "\n".join(
                        f'<div class="skill-category"><strong>{cat.split(":")[0].strip()}:</strong>{cat.split(":")[1].strip() if ":" in cat else cat}</div>'
                        for cat in st.session_state['resume_skills_content'].split("\n") if cat.strip()
                    ) if st.session_state['resume_skills_content'] else ""
                    
                    linkedin_html = f'<a href="{linkedin}">LinkedIn</a>' if linkedin else ""
                    github_html = f'<a href="{github}">GitHub</a>' if github else ""
                    
                    final_name = name
                    project_names = [p[0].strip().lower() for p in st.session_state['projects'] if p[0].strip()]
                    if final_name.strip().lower() in project_names:
                        st.error(f"Error: Name '{final_name}' matches a project name. Please verify your name.")
                        st.stop()

                    template_data = {
                        "name": final_name,
                        "phone": phone,
                        "email": email,
                        "linkedin_html": linkedin_html,
                        "github_html": github_html,
                        "university": edu[0],
                        "education_dates": edu[2],
                        "degree": edu[1],
                        "gpa": f" | <strong>GPA:</strong> {edu[3]}" if edu[3] else "",
                        "university_location": edu[4],
                        "education_bullets": edu_bullets,
                        "skills_content": skills_formatted,
                        "job1_title": final_work[0][0] if final_work else "",
                        "job1_dates": final_work[0][2] if final_work else "",
                        "job1_company": final_work[0][1] if final_work else "",
                        "job1_location": final_work[0][3] if final_work else "",
                        "job1_bullets": job1_bullets,
                        "job2_title": final_work[1][0] if len(final_work) > 1 else "",
                        "job2_dates": final_work[1][2] if len(final_work) > 1 else "",
                        "job2_company": final_work[1][1] if len(final_work) > 1 else "",
                        "job2_location": final_work[1][3] if len(final_work) > 1 else "",
                        "job2_bullets": job2_bullets,
                        "project1_name": final_projects[0][0] if final_projects else "",
                        "project1_date": final_projects[0][1] if final_projects else "",
                        "project1_context": final_projects[0][2] if final_projects else "",
                        "project1_bullets": project1_bullets,
                        "project2_name": final_projects[1][0] if len(final_projects) > 1 else "",
                        "project2_date": final_projects[1][1] if len(final_projects) > 1 else "",
                        "project2_context": final_projects[1][2] if len(final_projects) > 1 else "",
                        "project2_bullets": project2_bullets
                    }
                    
                    html_resume = RESUME_TEMPLATE.format(**template_data)
                    pdf_bytes = generate_pdf(html_resume)
                    
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
                
                except KeyError as ke:
                    st.error(f"Template error: Missing placeholder '{ke.args[0]}'")
                except Exception as e:
                    st.error(f"Error generating resume: {str(e)}")

with tab2:
    st.subheader("Cover Letter Generator")
    job_desc = st.text_area("Paste Job Description*", height=200,
                            help="Copy and paste the job posting you're applying for",
                            placeholder="Paste the full job description here...",
                            key="cover_letter_job_desc")
    
    with st.expander("✉️ Cover Letter Details", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            hiring_manager = st.text_input("Hiring Manager Name (if known)", placeholder="Jason Sung")
            company_name = st.text_input("Company Name*", placeholder="Tech Innovations Inc.")
            company_address = st.text_input("Company Street Address", placeholder="123 Main Street")
        with col2:
            job_title = st.text_input("Job Title*", placeholder="Senior Software Engineer")
            your_name = st.text_input("Your Name*", value=st.session_state.get("resume_name", ""))
            company_city_state_zip = st.text_area("City, State ZIP Code", placeholder="New York, NY 10001")

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