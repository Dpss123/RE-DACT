import streamlit as st
import re
import io
from docx import Document
import pdfplumber
from fpdf import FPDF
from PIL import Image, ImageOps
import pytesseract
import time

# Set Tesseract path if needed:
# pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'

# --------- Helper functions ---------

def extract_text_from_word(file):
    doc = Document(file)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # Extract text with layout preserved (line breaks, spacing)
            page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
            if page_text:
                text += page_text + '\n\n'
    return text.strip()

def extract_text_from_image(image_file):
    # Open and preprocess image for better OCR accuracy
    img = Image.open(image_file)
    # Convert to grayscale and enhance contrast
    img = ImageOps.grayscale(img)
    # Optional: img = img.resize((img.width*2, img.height*2)) # Uncomment to enlarge image for better OCR
    
    # OCR with page segmentation mode 6 (assumes a uniform block of text)
    config = "--psm 6"
    text = pytesseract.image_to_string(img, config=config)
    return text.strip()

def mask_sensitive_data(text, selected_patterns):
    regex_patterns = {
        "Aadhaar Number": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        "PAN Number": r"\b[A-Z]{5}\d{4}[A-Z]{1}\b",
        "Phone Number": r"\b(\+91[\-\s]?)?[6-9]\d{9}\b",
        "Email Address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
    }
    masked_text = text
    for pattern_name in selected_patterns:
        regex = regex_patterns.get(pattern_name)
        if regex:
            def replacer(match):
                return '*' * len(match.group())
            masked_text = re.sub(regex, replacer, masked_text)
    return masked_text

def generate_masked_pdf(text):
    # Use FPDF to keep multiline and format intact (monospaced font)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Courier", size=11)  # Monospace font to preserve layout approx

    # Split text into lines, add line by line
    lines = text.split('\n')
    line_height = pdf.font_size * 1.5

    for line in lines:
        pdf.multi_cell(0, line_height, line)

    pdf_buffer = io.BytesIO()
    pdf.output(pdf_buffer)
    pdf_buffer.seek(0)
    return pdf_buffer

# --------- Streamlit UI & Logic ---------

st.set_page_config(page_title="AI-Powered Sensitive Data Masking", layout="centered")

# Custom CSS (kept simple for clarity)
st.markdown("""
<style>
    body {
        background: #0a0f1a url('https://images.unsplash.com/photo-1504384308090-c894fdcc538d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1470&q=80') no-repeat center fixed;
        background-size: cover;
        color: #e0e6f0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        color: #4ade80;
        text-shadow:
          0 0 5px #4ade80,
          0 0 10px #4ade80,
          0 0 20px #22c55e,
          0 0 30px #16a34a,
          0 0 40px #16a34a;
        margin-bottom: 0.2rem;
        letter-spacing: 2px;
    }
    .subtitle {
        font-size: 1.3rem;
        color: #a3f5a3cc;
        margin-top: 0;
        margin-bottom: 2rem;
        text-shadow: 0 0 3px #4ade80aa;
    }
    .stFileUploader > div > label > div {
        background-color: #1f2937cc;
        border-radius: 1rem;
        padding: 1.25rem;
        font-weight: 700;
        border: 2px solid #22c55e;
        transition: all 0.4s ease;
        box-shadow: 0 0 8px #22c55e99;
    }
    .stFileUploader > div > label > div:hover {
        background-color: #22c55e;
        color: #111827;
        cursor: pointer;
        box-shadow: 0 0 15px #4ade80;
        transform: scale(1.05);
    }
    div.stButton > button:first-child {
        background: linear-gradient(90deg, #22c55e 0%, #4ade80 100%);
        color: #111827;
        font-weight: 900;
        font-size: 1.1rem;
        padding: 0.9rem 2.5rem;
        border-radius: 2rem;
        border: none;
        box-shadow:
          0 0 10px #4ade80,
          0 0 20px #22c55e,
          0 0 40px #16a34a;
        transition: all 0.3s ease;
        letter-spacing: 1.2px;
    }
    div.stButton > button:first-child:hover {
        background: linear-gradient(90deg, #16a34a 0%, #22c55e 100%);
        color: white;
        cursor: pointer;
        box-shadow:
          0 0 20px #22c55e,
          0 0 40px #4ade80,
          0 0 60px #4ade80;
        transform: scale(1.05);
    }
    .stTextArea textarea {
        background-color: #15232c !important;
        color: #d1d5db !important;
        border-radius: 1rem !important;
        font-size: 1rem !important;
        box-shadow: inset 0 0 12px #22c55e66;
        border: none !important;
        padding: 1rem !important;
        line-height: 1.4rem !important;
        font-family: 'Courier New', monospace !important;
        white-space: pre-wrap;
    }
    .stDownloadButton > button {
        background-color: #2563eb;
        color: white;
        font-weight: 700;
        border-radius: 1.5rem;
        padding: 0.75rem 1.8rem;
        box-shadow: 0 0 8px #2563ebaa;
        transition: all 0.3s ease;
    }
    .stDownloadButton > button:hover {
        background-color: #1d4ed8;
        cursor: pointer;
        box-shadow: 0 0 15px #1d4ed8cc;
    }
    .card {
        background-color: #15232cdd;
        border-radius: 1.5rem;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow:
          0 4px 10px rgba(34, 197, 94, 0.25),
          0 0 15px #22c55e88;
        transition: transform 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow:
          0 8px 20px rgba(34, 197, 94, 0.5),
          0 0 25px #4ade80aa;
    }
    .loading-spinner {
        border: 5px solid #15232c;
        border-top: 5px solid #22c55e;
        border-radius: 50%;
        width: 40px;
        height: 40px;
        animation: spin 1.2s linear infinite;
        margin: 1rem auto;
    }
</style>
""", unsafe_allow_html=True)

# Header
header_col1, header_col2 = st.columns([1, 6])
with header_col1:
    st.image("https://img.icons8.com/external-flaticons-lineal-color-flat-icons/64/4ade80/external-ai-artificial-intelligence-flaticons-lineal-color-flat-icons.png", width=60)
with header_col2:
    st.markdown('<h1 class="main-title">AI-Powered Sensitive Data Masking</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Upload documents or images to securely mask sensitive information instantly.</p>', unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("📂 Upload Word, PDF, or Image file", type=["docx", "pdf", "png", "jpg", "jpeg"])

    if uploaded_file:
        file_type = uploaded_file.type
        mask_options = ["Aadhaar Number", "PAN Number", "Phone Number", "Email Address"]
        selected_masks = st.multiselect("Select sensitive data types to mask", options=mask_options, default=mask_options)

        if st.button("Mask Sensitive Data"):
            with st.spinner("Processing..."):
                time.sleep(0.5)  # Spinner visibility

                try:
                    if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                        text = extract_text_from_word(uploaded_file)
                    elif file_type == "application/pdf":
                        text = extract_text_from_pdf(uploaded_file)
                    elif file_type.startswith("image/"):
                        text = extract_text_from_image(uploaded_file)
                    else:
                        st.error("Unsupported file type.")
                        text = ""
                except Exception as e:
                    st.error(f"Error extracting text: {e}")
                    text = ""

                if text:
                    masked_text = mask_sensitive_data(text, selected_masks)
                    st.markdown("### Masked Text Output:")
                    st.text_area("", masked_text, height=300)

                    pdf_buffer = generate_masked_pdf(masked_text)
                    st.download_button(
                        label="📥 Download Masked PDF",
                        data=pdf_buffer,
                        file_name="masked_output.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("No text extracted from the uploaded file.")

    else:
        st.markdown("### Please upload a Word, PDF, or Image file to get started 👆")

    st.markdown("</div>", unsafe_allow_html=True)

# Footer
st.markdown("""
<footer style='text-align:center; padding:10px; color:#4ade80;'>
    Developed by Dheerendra Pratap Singh &nbsp;&nbsp;|&nbsp;&nbsp; Powered by AI & NLP
</footer>
""", unsafe_allow_html=True)

