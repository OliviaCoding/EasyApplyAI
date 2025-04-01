import streamlit as st
import re
from datetime import datetime
from functools import lru_cache
from openai import OpenAI
from weasyprint import HTML
import tempfile
import base64

# Utility function to create safe filenames
def sanitize_filename(text, default="file"):
    """Generate filesystem-safe filenames."""
    name_part = text.split('\n')[0].strip() if text else default
    safe_name = re.sub(r'[^\w-]', '_', name_part)[:50]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{safe_name}_{timestamp}"

# Configure Streamlit page settings
st.set_page_config(page_title="AI Resume Generator", layout="wide")
st.title("📄 Professional Resume & Cover Letter Generator")

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Compact HTML template with one-page optimized styling
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Professional Resume</title>
    <style>
        body {{
            font-family: 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.4;
            color: #333;
            max-width: 750px;
            margin: 0 auto;
            padding: 10px;
            font-size: 12px;
        }}
        .header {{
            text-align: center;
            margin-bottom: 8px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 6px;
        }}
        .name {{
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 3px;
        }}
        .contact-info {{
            font-size: 11px;
            color: #7f8c8d;
            margin-bottom: 5px;
        }}
        .contact-line {{
            margin: 3px 0;
        }}
        .section {{
            margin-bottom: 10px;
        }}
        .section-title {{
            font-size: 14px;
            font-weight: bold;
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 3px;
            margin-bottom: 6px;
            text-transform: uppercase;
        }}
        .subsection {{
            margin-bottom: 8px;
        }}
        .job-title {{
            font-weight: bold;
            font-size: 12px;
        }}
        .company {{
            font-style: italic;
            font-size: 11px;
        }}
        .dates {{
            float: right;
            font-weight: normal;
        }}
        .location {{
            font-style: italic;
            color: #7f8c8d;
            font-size: 11px;
        }}
        ul {{
            margin-top: 3px;
            padding-left: 15px;
        }}
        li {{
            margin-bottom: 3px;
            font-size: 11px;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        .skills-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            font-size: 11px;
        }}
        .skill-category {{
            margin-bottom: 4px;
        }}
        .skill-category strong {{
            display: inline-block;
            margin-right: 5px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="name">{name}</div>
        <div class="contact-info">
            <div class="contact-line">📱 {phone} | ✉️ <a href="mailto:{email}">{email}</a></div>
            <div class="contact-line">
                {linkedin_html} | {github_html}
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Education</div>
        <div class="subsection">
            <div class="job-title">{university} <span class="dates">{education_dates}</span></div>
            <div class="company">{degree}{gpa}</div>
            <div class="location">{university_location}</div>
            <ul>
                {education_bullets}
            </ul>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Technical Skills</div>
        <div class="skills-list">
            {skills_content}
        </div>
    </div>

    <div class="section">
        <div class="section-title">Experience</div>
        <div class="subsection">
            <div class="job-title">{job1_title} <span class="dates">{job1_dates}</span></div>
            <div class="company">{job1_company}</div>
            <div class="location">{job1_location}</div>
            <ul>
                {job1_bullets}
            </ul>
        </div>
        <div class="subsection">
            <div class="job-title">{job2_title} <span class="dates">{job2_dates}</span></div>
            <div class="company">{job2_company}</div>
            <div class="location">{job2_location}</div>
            <ul>
                {job2_bullets}
            </ul>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Projects</div>
        <div class="subsection">
            <div class="job-title">{project1_name} <span class="dates">{project1_date}</span></div>
            <div class="company">{project1_context}</div>
            <ul>
                {project1_bullets}
            </ul>
        </div>
        <div class="subsection">
            <div class="job-title">{project2_name} <span class="dates">{project2_date}</span></div>
            <div class="company">{project2_context}</div>
            <ul>
                {project2_bullets}
            </ul>
        </div>
    </div>
</body>
</html>
"""
# Compact Cover Letter HTML template with one-page optimized styling

COVER_LETTER_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Cover Letter</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            margin-bottom: 20px;
        }}
        .contact-info {{
            margin-bottom: 5px;
        }}
        .date {{

            margin-bottom: 20px;
        }}
        .recipient {{
            margin-bottom: 20px;
        }}
        .salutation {{
            margin-bottom: 10px;
        }}
        .content {{
            margin-bottom: 20px;
            white-space: pre-wrap;
        }}
        .signature {{
            margin-top: 40px;
        }}
    </style>
</head>
<body>
    <div class="date">{date}</div>

    <div class="recipient">
        <div>{recipient_name}</div>
        <div>{company_name}</div>
        <div>{company_address}</div>
        <div>{company_city_state_zip}</div>
    </div>

    <div class="salutation">{salutation}</div>

    <div class="content">{content}</div>

    <div class="signature">
        <div>Sincerely,</div>
        <div><strong>{name}</strong></div>
    </div>
</body>
</html>
"""

def generate_bullet_points(prompt_text, max_bullets=3, job_desc=None):
    """Generate achievement bullet points using OpenAI API with optional job description tailoring"""
    try:
        prompt = f"Convert this work experience into {max_bullets} professional achievement bullet points for a resume. Use strong action verbs and quantify results when possible."
        
        if job_desc:
            prompt += f"\n\nTailor these bullet points to match the following job description:\n{job_desc}\n\n"
        
        prompt += f"Return only the bullet points with no additional text, each on a new line:\n\n{prompt_text}"
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            temperature=0.4,
            max_tokens=300
        )
        bullets = response.choices[0].message.content.strip().split('\n')
        return "\n".join([f"<li>{b.strip('-• ')}</li>" for b in bullets[:max_bullets] if b.strip()])
    except Exception as e:
        st.error(f"Failed to generate bullet points: {str(e)}")
        return "<li>Error generating bullet points</li>"

def generate_cover_letter(info, job_desc):
    """
    Generate tailored cover letter body content (without salutation/closing) using OpenAI API
    Returns: Generated text or None if failed
    """
    prompt = f"""
    Write ONLY the body content of a professional cover letter (3-4 paragraphs) based on:
    
    ---CANDIDATE PROFILE---
    {info}
    
    ---JOB DESCRIPTION---
    {job_desc}
    
    IMPORTANT INSTRUCTIONS:
    1. DO NOT include any letter formatting (no "Dear...", no "Sincerely")
    2. Focus on matching candidate skills to job requirements
    3. First paragraph should express interest and highlight most relevant qualification
    4. Middle paragraphs should demonstrate relevant experience/skills
    5. Final paragraph should include call to action and express enthusiasm
    6. Use professional but conversational tone
    7. Keep it concise (about 200-300 words total)
    8. Quantify achievements where possible
    9. Do not repeat information verbatim from resume
    
    Return ONLY the cover letter body content, nothing else.
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
        st.error(f"Cover letter generation failed: {str(e)}")
        return None

def generate_pdf(html_content):
    """Generate PDF from HTML content with proper styling"""
    try:
        html = HTML(string=html_content)
        pdf_bytes = html.write_pdf()
        return pdf_bytes
    except Exception as e:
        st.error(f"PDF generation failed: {str(e)}")
        return None

# Main form tabs
tab1, tab2 = st.tabs(["📝 Resume Builder", "✉️ Cover Letter Generator"])

with tab1:
    # Detailed Questionnaire Form for Resume
    with st.expander("🔍 Personal Information", expanded=True):
        st.subheader("Contact Information")
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Full Name*", placeholder="Grace Hopper", key="resume_name")
        with col2:
            phone = st.text_input("Phone Number*", placeholder="(123) 456-7890", key="resume_phone")
        with col3:
            email = st.text_input("Email*", placeholder="your.email@example.com", key="resume_email")
        
        col4, col5 = st.columns(2)
        with col4:
            linkedin = st.text_input("LinkedIn URL", placeholder="https://linkedin.com/in/your-profile", key="resume_linkedin")
        with col5:
            github = st.text_input("GitHub URL", placeholder="https://github.com/your-username", key="resume_github")

    with st.expander("🎓 Education"):
        st.subheader("Primary Education")
        col1, col2 = st.columns(2)
        with col1:
            university = st.text_input("University Name*", placeholder="University of North Carolina at Chapel Hill", key="resume_university")
        with col2:
            degree = st.text_input("Degree*", placeholder="B.S. Computer Science", key="resume_degree")
        
        col3, col4, col5 = st.columns(3)
        with col3:
            education_dates = st.text_input("Dates Attended*", placeholder="Aug. 2021 -- May 2025", key="resume_education_dates")
        with col4:
            gpa = st.text_input("GPA", placeholder="3.8/4.0", key="resume_gpa")
        with col5:
            university_location = st.text_input("Location*", placeholder="Chapel Hill, NC", key="resume_university_location")
        
        education_bullets = st.text_area("Additional Education Details", height=100,
            help="Include: Honors, awards, relevant courses (one per line)",
            placeholder="Dean's List\nRelevant Courses: Data Structures, Algorithms",
            key="resume_education_bullets")

    with st.expander("💼 Work Experience"):
        st.subheader("Most Recent Position")
        col1, col2 = st.columns(2)
        with col1:
            job1_title = st.text_input("Job Title*", placeholder="Software Engineer Intern", key="resume_job1_title")
        with col2:
            job1_company = st.text_input("Company Name*", placeholder="Tech Company Inc.", key="resume_job1_company")
        
        col3, col4 = st.columns(2)
        with col3:
            job1_dates = st.text_input("Employment Dates*", placeholder="May 2023 -- Aug. 2023", key="resume_job1_dates")
        with col4:
            job1_location = st.text_input("Location*", placeholder="San Francisco, CA", key="resume_job1_location")
        
        job1_desc = st.text_area("Job Description & Achievements*", height=150,
            help="Describe your responsibilities and accomplishments (we'll convert to bullet points)",
            placeholder="Developed new features for company platform using Python and React\nOptimized database queries reducing response time by 30%",
            key="resume_job1_desc")
        
        st.subheader("Second Most Recent Position")
        col5, col6 = st.columns(2)
        with col5:
            job2_title = st.text_input("Job Title", placeholder="Teaching Assistant", key="resume_job2_title")
        with col6:
            job2_company = st.text_input("Company Name", placeholder="University CS Department", key="resume_job2_company")
        
        col7, col8 = st.columns(2)
        with col7:
            job2_dates = st.text_input("Employment Dates", placeholder="Aug. 2022 -- May 2023", key="resume_job2_dates")
        with col8:
            job2_location = st.text_input("Location", placeholder="Chapel Hill, NC", key="resume_job2_location")
        
        job2_desc = st.text_area("Job Description & Achievements", height=150,
            help="Describe your responsibilities and accomplishments",
            placeholder="Mentored 50+ students in introductory programming\nCreated new course materials improving exam scores by 15%",
            key="resume_job2_desc")

    with st.expander("🛠 Skills"):
        skills_content = st.text_area("Technical Skills*", height=100,
            help="List in this format: Languages: Java, Python | Technologies: React, Docker | Tools: Git, Jira",
            placeholder="Languages: Java, Python (pandas, matplotlib)\nTechnologies: React, Node.js, Docker\nTools: Git, Jira, Figma",
            key="resume_skills_content")

    with st.expander("🚀 Projects"):
        st.subheader("Project 1")
        col1, col2 = st.columns(2)
        with col1:
            project1_name = st.text_input("Project Name", placeholder="RESTroom Yelp", key="resume_project1_name")
        with col2:
            project1_date = st.text_input("Completion Date", placeholder="Feb. 2023", key="resume_project1_date")
        
        project1_context = st.text_input("Project Context", placeholder="UNC PearlHacks", key="resume_project1_context")
        project1_desc = st.text_area("Project Description", height=100,
            help="Describe the project and your contributions",
            placeholder="Developed a web app for finding and rating campus restrooms\nWon 1st place in university hackathon",
            key="resume_project1_desc")
        
        st.subheader("Project 2")
        col3, col4 = st.columns(2)
        with col3:
            project2_name = st.text_input("Project Name", placeholder="Discover the New World", key="resume_project2_name")
        with col4:
            project2_date = st.text_input("Completion Date", placeholder="May 2022", key="resume_project2_date")
        
        project2_context = st.text_input("Project Context", placeholder="Console Mini-Game", key="resume_project2_context")
        project2_desc = st.text_area("Project Description", height=100,
            help="Describe the project and your contributions",
            placeholder="Created a text-based adventure game in C#\nImplemented random map generation algorithm",
            key="resume_project2_desc")

    # Generate Resume Button
    if st.button("✨ Generate Professional Resume", type="primary", key="generate_resume_btn"):
        if not name or not university or not degree or not job1_title or not job1_company:
            st.error("Please fill in all required fields (marked with *)")
        else:
            with st.spinner("Generating your professional resume..."):
                try:
                    # Generate bullet points for each section
                    job1_bullets = generate_bullet_points(job1_desc, max_bullets=3) if job1_desc else ""
                    job2_bullets = generate_bullet_points(job2_desc, max_bullets=2) if job2_desc else ""
                    project1_bullets = generate_bullet_points(project1_desc, max_bullets=2) if project1_desc else ""
                    project2_bullets = generate_bullet_points(project2_desc, max_bullets=2) if project2_desc else ""
                    
                    # Format education bullets (limited to 3 to save space)
                    if education_bullets:
                        edu_lines = [line.strip() for line in education_bullets.split('\n') if line.strip()]
                        edu_bullets = "\n".join([f"<li>{line}</li>" for line in edu_lines[:3]])
                    else:
                        edu_bullets = ""
                    
                    # Format skills content more compactly
                    if skills_content:
                        skills_formatted = "\n".join([
                            f'<div class="skill-category"><strong>{cat.split(":")[0].strip()}:</strong>{cat.split(":")[1].strip()}</div>'
                            for cat in skills_content.split("\n") if ":" in cat
                        ])
                    else:
                        skills_formatted = '<div class="skill-category"><strong>Languages:</strong> Python, Java</div>'
                    
                    # Format contact links
                    linkedin_html = f'<a href="{linkedin}">LinkedIn</a>' if linkedin else "LinkedIn: Not provided"
                    github_html = f'<a href="{github}">GitHub</a>' if github else "GitHub: Not provided"
                    
                    # Replace all placeholders in template
                    html_resume = HTML_TEMPLATE.format(
                        name=name,
                        phone=phone,
                        email=email,
                        linkedin_html=linkedin_html,
                        github_html=github_html,
                        university=university,
                        education_dates=education_dates,
                        degree=degree,
                        gpa=f" | <strong>GPA:</strong> {gpa}" if gpa else "",
                        university_location=university_location,
                        education_bullets=edu_bullets,
                        skills_content=skills_formatted,
                        job1_title=job1_title,
                        job1_dates=job1_dates,
                        job1_company=job1_company,
                        job1_location=job1_location,
                        job1_bullets=job1_bullets,
                        job2_title=job2_title if job2_title else "Position",
                        job2_dates=job2_dates if job2_dates else "Dates",
                        job2_company=job2_company if job2_company else "Company",
                        job2_location=job2_location if job2_location else "Location",
                        job2_bullets=job2_bullets if job2_bullets else "<li>Description</li>",
                        project1_name=project1_name if project1_name else "Project Name",
                        project1_context=project1_context if project1_context else "Context",
                        project1_date=project1_date if project1_date else "Date",
                        project1_bullets=project1_bullets if project1_bullets else "<li>Description</li>",
                        project2_name=project2_name if project2_name else "Project Name",
                        project2_context=project2_context if project2_context else "Context",
                        project2_date=project2_date if project2_date else "Date",
                        project2_bullets=project2_bullets if project2_bullets else "<li>Description</li>",
                    )
                    
                    # Generate PDF
                    pdf_bytes = generate_pdf(html_resume)
                    
                    # Display and download options
                    st.subheader("Your Professional Resume")
                    
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
                    
                    # Display HTML preview
                    st.components.v1.html(html_resume, height=800, scrolling=True)
                    
                except Exception as e:
                    st.error("Error generating resume")
                    st.exception(e)

with tab2:
    # Cover Letter Generator
    st.subheader("Cover Letter Generator")
    
    # Get job description from resume tab or allow new input
    job_desc = st.text_area("Paste Job Description*", height=200,
        help="Copy and paste the job posting you're applying for",
        placeholder="Paste the full job description here...")
    
    # Additional cover letter specific fields
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

    # Generate Cover Letter Button
    if st.button("✍️ Generate Cover Letter", type="primary", key="generate_cover_letter_btn"):
        if not job_desc or not company_name or not job_title or not your_name:
            st.error("Please fill in all required fields (marked with *)")
        else:
            with st.spinner("Generating your tailored cover letter..."):
                try:
                    # Get all user information from session state
                    user_email = st.session_state.get("resume_email", "[Email]")
                
                    # Compile candidate info from resume form
                    candidate_info = f"""
                    Candidate Name: {your_name}
        
                    
                    Education:
                    - {st.session_state.get("resume_degree", "")} at {st.session_state.get("resume_university", "")}
                    
                    Work Experience:
                    - {st.session_state.get("resume_job1_title", "")} at {st.session_state.get("resume_job1_company", "")}
                    - {st.session_state.get("resume_job2_title", "")} at {st.session_state.get("resume_job2_company", "")}
                    
                    Skills:
                    {st.session_state.get("resume_skills_content", "")}
                    """
                    
                    # Generate cover letter content only (without headers/footers)
                    cover_letter_content = generate_cover_letter(candidate_info, job_desc)
                    
                    if cover_letter_content:
                        # Create professional letter format with all user info
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
                        # Save to session state
                        st.session_state['formatted_letter'] = formatted_letter
                        st.session_state['cover_letter_content'] = cover_letter_content
                        st.session_state['cover_letter_generated'] = True
                        
                        # Create HTML version for PDF
                        html_letter = COVER_LETTER_HTML_TEMPLATE.format(
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

    # Display cover letter if it exists in session state
    if st.session_state.get('cover_letter_generated', False):
        st.subheader("Your Tailored Cover Letter")
        st.text_area("Preview", st.session_state['formatted_letter'], height=500, key="cover_letter_preview")
        
        # Download options
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
1. Fill in all required fields (*)
2. Provide detailed work experience
3. Click "Generate Professional Resume"
4. Download PDF or HTML version

**Cover Letter Generator:**
1. Paste the job description
2. Fill in company details
3. Click "Generate Cover Letter"
4. Download TXT or PDF version

## 💡 Tips for Best Results
- Use action verbs (Developed, Led, Optimized)
- Quantify achievements when possible
- Keep bullet points concise (1 line each)
- Tailor both resume and cover letter to each job
""")