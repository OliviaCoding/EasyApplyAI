![Python](https://img.shields.io/badge/python-3.9+-blue)
![Streamlit](https://img.shields.io/badge/streamlit-1.25+-green)
[![GitHub stars](https://img.shields.io/github/stars/OliviaCoding/EasyApplyAI?style=social)](https://github.com/OliviaCoding/EasyApplyAI)
[![Open Issues](https://img.shields.io/github/issues/OliviaCoding/EasyApplyAI)](https://github.com/OliviaCoding/EasyApplyAI/issues)

# EasyApplyAI - Professional Resume & Cover Letter Generator

🚀 A Streamlit-powered web application for generating tailored resumes and cover letters with AI assistance.

## ✨ Enhanced Features

- **Structured Resume Builder**: Guided form with sections for:
  - Personal information
  - Education history
  - Work experience (2 positions)
  - Technical skills
  - Projects (2 entries)
- **AI-Powered Content Generation**:
  - GPT-3.5 optimized bullet points
  - Job description-tailored content
  - Professional cover letter generation
- **Multiple Output Formats**:
  - Professionally styled PDF resumes
  - HTML source files
  - Plain text cover letters
- **One-Page Optimized Design**: Clean, ATS-friendly templates
- **Smart Filename Generation**: Auto-includes name and timestamp

## 🛠️ Technology Stack

| Component       | Version | Purpose |
|----------------|---------|---------|
| Python         | 3.9+    | Backend |
| Streamlit      | 1.25+   | UI Framework |
| WeasyPrint     | 56.1    | PDF Generation |
| OpenAI API     | Latest  | AI Content |
| lru_cache      | Built-in| API Call Optimization |

## 🚀 Installation

```bash
git clone https://github.com/OliviaCoding/EasyApplyAI.git
cd EasyApplyAI
pip install -r requirements.txt
```

## 💻 Usage
```bash
streamlit run app.py
```
Then open the local URL shown in your terminal (typically http://localhost:8501)

## 📂 Project Structure
```
/resume-generator
├── app.py          # Main Streamlit application
├── requirements.txt # Python dependencies
├── assets/         # HTML templates and styling
├── .streamlit/     # Streamlit configuration
└── secrets.toml    # API credentials (example)
```
## 🔧 Development Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows
```

## 📜 License
[GPL-3.0](LICENSE) © 2025 Wanying Xu