import streamlit as st
import re
import io
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageFilter
import pytesseract

# Function to extract text from Word documents
def extract_text_from_word(doc_file):
    doc = Document(doc_file)
    return [p.text for p in doc.paragraphs], doc

# Function to extract text from PDF documents
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    return [page.extract_text() or "" for page in reader.pages]

# Function to mask sensitive data in text
def mask_sensitive_data(paragraphs, selected_options):
    regex_patterns = {
        "Emails": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
        "Phone Numbers": r'\b\d{10}\b',
        "Account Numbers": r'\b\d{11,14}\b',
        "IFSC Codes": r'\b[A-Z]{4}\d{7}\b'
    }
    masked = []
    for para in paragraphs:
        for opt in selected_options:
            para = re.sub(regex_patterns.get(opt, ''), '[DATA HIDDEN]', para)
        masked.append(para)
    return masked

# Function to create Word document with masked data
def create_word(masked_paragraphs):
    buffer = io.BytesIO()
    doc = Document()
    for para in masked_paragraphs:
        doc.add_paragraph(para)
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# Function to create PDF with masked data
def create_pdf(masked_paragraphs):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    text = c.beginText(40, 750)
    for para in masked_paragraphs:
        for line in para.split("\n"):
            text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

# Function to blur sensitive data areas in image
def blur_area(image, box):
    region = image.crop(box)
    blurred = region.filter(ImageFilter.GaussianBlur(radius=5))
    image.paste(blurred, box)

# Function to process image by blurring sensitive data
def process_image(image, selected_options):
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    patterns = {
        "Emails": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
        "Phone Numbers": r'\b\d{10}\b',
        "Account Numbers": r'\b\d{11,14}\b',
        "IFSC Codes": r'\b[A-Z]{4}\d{7}\b'
    }
    for i, word in enumerate(data['text']):
        for opt in selected_options:
            pattern = patterns.get(opt)
            if pattern and re.fullmatch(pattern, word):
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                blur_area(image, (x, y, x + w, y + h))
    return image

st.title("🔒 Sensitive Data Redaction App")

uploaded_file = st.file_uploader("Upload a file (Word, PDF, Image)", type=["docx", "pdf", "png", "jpg", "jpeg"])

if uploaded_file:
    ftype = uploaded_file.type
    options = ["Emails", "Phone Numbers", "Account Numbers", "IFSC Codes"]

    if "wordprocessingml" in ftype:
        paragraphs, _ = extract_text_from_word(uploaded_file)
    elif ftype == "application/pdf":
        paragraphs = extract_text_from_pdf(uploaded_file)
    elif "image" in ftype:
        image = Image.open(uploaded_file)
        st.image(image, caption="Original Image", use_column_width=True)
        selected = st.multiselect("Select types to blur:", options)
        if st.button("Blur Sensitive Data"):
            if selected:
                result = process_image(image, selected)
                st.image(result, caption="Blurred Image", use_column_width=True)
                buf = io.BytesIO()
                result.save(buf, format="PNG")
                st.download_button("Download Blurred Image", buf.getvalue(), file_name="blurred.png")
            else:
                st.warning("Please select at least one data type to blur.")
        st.stop()
    else:
        st.error("Unsupported file type.")
        st.stop()

    st.subheader("Extracted Text")
    st.write("\n".join(paragraphs))

    selected = st.multiselect("Select types to redact:", options)
    if st.button("Redact Text"):
        if selected:
            masked = mask_sensitive_data(paragraphs, selected)
            st.subheader("Redacted Text")
            st.write("\n".join(masked))
            if "wordprocessingml" in ftype:
                st.download_button("Download Word", create_word(masked), "redacted.docx")
            elif ftype == "application/pdf":
                st.download_button("Download PDF", create_pdf(masked), "redacted.pdf")
        else:
            st.warning("Please select at least one data type to redact.")
