![Python](https://img.shields.io/badge/python-3.9+-blue)
![Flask](https://img.shields.io/badge/flask-2.0+-green)
[![GitHub stars](https://img.shields.io/github/stars/OliviaCoding/EasyApplyAI?style=social)](https://github.com/OliviaCoding/EasyApplyAI)
[![Open Issues](https://img.shields.io/github/issues/OliviaCoding/EasyApplyAI)](https://github.com/OliviaCoding/EasyApplyAI/issues)
# EasyApplyAI - Resume Generator

🚀 A Flask-based web application for automated resume generation and optimization.

## Features
- **Resume Templating**: Pre-designed professional templates
- **AI Integration**: (Optional) AWS Bedrock/Titan embeddings for content suggestions
- **PDF Export**: One-click download in standard formats
- **Responsive Design**: Works on desktop and mobile

## 🛠️ Technologies
| Component       | Version |
|----------------|---------|
| Python         | 3.9+    |
| Flask          | 2.0+    |
| Bootstrap      | 5.1     |
| PDFKit         | 0.6.1   |

## Installation
```bash
git clone https://github.com/OliviaCoding/EasyApplyAI.git
cd EasyApplyAI
pip install -r requirements.txt
```

## Usage
```bash
python app.py
```
Then open `http://localhost:5000` in your browser.

## Project Structure
```
/resume-generator
├── app.py          # Flask main application
├── requirements.txt # Dependencies
├── static/         # CSS/JS/Images
└── templates/      # HTML templates
```
## Development
```bash
# Set up virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate    # Windows

## License
[GPL-3.0](LICENSE) © 2025 Wanying Xu