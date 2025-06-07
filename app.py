#!/usr/bin/env python
# coding: utf-8

# In[13]:


with open("app.py", "w") as file:
    file.write('''
import streamlit as st
import re
import io
from docx import Document
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFilter
import pytesseract
import cv2
import numpy as np
from moviepy.editor import ImageSequenceClip

# Function to extract text from Word documents
def extract_text_from_word(doc_file):
    doc = Document(doc_file)
    paragraphs = []
    for para in doc.paragraphs:
        paragraphs.append(para.text)
    return paragraphs, doc

# Function to extract text from PDF documents
def extract_text_from_pdf(pdf_file):
    reader = PdfReader(pdf_file)
    paragraphs = []
    for page in reader.pages:
        paragraphs.append(page.extract_text())
    return paragraphs

# Function to mask sensitive data in text
def mask_sensitive_data(paragraphs, selected_options):
    regex_patterns = {
        "Emails": r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.com\\b',
        "Phone Numbers": r'\\b\\d{10}\\b',  # Exactly 10 digits
        "Account Numbers": r'\\b\\d{11,14}\\b',  # Between 11 and 14 digits
        "IFSC Codes": r'\\b[A-Z]{4}\\d{7}\\b'
    }
    
    masked_paragraphs = []
    for paragraph in paragraphs:
        masked_paragraph = paragraph
        for option in selected_options:
            if option in regex_patterns:
                masked_paragraph = re.sub(regex_patterns[option], '[DATA HIDDEN]', masked_paragraph)
        masked_paragraphs.append(masked_paragraph)
    
    return masked_paragraphs

# Function to create Word document with masked data
def create_word(masked_paragraphs):
    buffer = io.BytesIO()
    new_doc = Document()
    for paragraph in masked_paragraphs:
        new_doc.add_paragraph(paragraph)
    new_doc.save(buffer)
    buffer.seek(0)
    return buffer

# Function to create PDF with masked data
def create_pdf(masked_paragraphs):
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=letter)
    text_object = pdf_canvas.beginText(40, 750)
    for paragraph in masked_paragraphs:
        lines = paragraph.split("\\n")
        for line in lines:
            text_object.textLine(line)
    pdf_canvas.drawText(text_object)
    pdf_canvas.showPage()
    pdf_canvas.save()
    buffer.seek(0)
    return buffer

# Function to blur 
def blur_area(image, box):
    region = image.crop(box)
    blurred_region = region.filter(ImageFilter.GaussianBlur(radius=5))
    image.paste(blurred_region, box)

# Function to process image 
def process_image(image, selected_options):
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    patterns = {
        "Emails": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+',
        "Phone Numbers": r'\\b\\d{10}\\b',
        "Account Numbers": r'\\b\\d{11,14}\\b',
        "IFSC Codes": r'\\b[A-Z]{4}\\d{7}\\b'
    }
    
    for i, text in enumerate(data['text']):
        for option in selected_options:
            if re.match(patterns.get(option, ''), text):
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                blur_area(image, (x, y, x + w, y + h))
    return image

# Function to process a single frame for sensitive data
def process_frame(frame, selected_options):
    image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    
    pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files\\Tesseract-OCR\\tesseract.exe'
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    patterns = {
        "Emails": r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\\.[a-zA-Z0-9-.]+',
        "Phone Numbers": r'\\b\\d{10}\\b',
        "Account Numbers": r'\\b\\d{11,14}\\b',
        "IFSC Codes": r'\\b[A-Z]{4}\\d{7}\\b'
    }
    
    for i, text in enumerate(data['text']):
        for option in selected_options:
            if re.match(patterns.get(option, ''), text):
                x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
                blur_area(image, (x, y, x + w, y + h))
    
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

# Function to process video 
def process_video(video_path, selected_options):
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        processed_frame = process_frame(frame, selected_options)
        frames.append(processed_frame)
    
    cap.release()
    return frames

st.title("Sensitive Data Masking in Files, Images, and Videos")

# File uploader for Word, PDF, Image, or Video
uploaded_file = st.file_uploader("Upload a Word, PDF, Image, or Video file", type=["docx", "pdf", "png", "jpg", "jpeg", "mp4", "avi", "mov"])

if uploaded_file is not None:
    file_type = uploaded_file.type
    if file_type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document", "application/pdf"]:
        if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            paragraphs, _ = extract_text_from_word(uploaded_file)
        elif file_type == "application/pdf":
            paragraphs = extract_text_from_pdf(uploaded_file)
        
        extracted_text = "\\n".join(paragraphs)
        st.subheader("Extracted Text:")
        st.write(extracted_text)
        
        options = ["Emails", "Phone Numbers", "Account Numbers", "IFSC Codes"]
        selected_options = st.multiselect("Select data types to mask:", options)

        if st.button("Mask Sensitive Data"):
            if selected_options:
                masked_paragraphs = mask_sensitive_data(paragraphs, selected_options)
                masked_text = "\\n".join(masked_paragraphs)
                st.subheader("Text with Sensitive Data Hidden:")
                st.write(masked_text)
                
                if file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                    word_buffer = create_word(masked_paragraphs)
                    st.download_button("Download Masked Word File", word_buffer, "masked_data.docx")
                elif file_type == "application/pdf":
                    pdf_buffer = create_pdf(masked_paragraphs)
                    st.download_button("Download Masked PDF File", pdf_buffer, "masked_data.pdf")
            else:
                st.warning("Please select at least one data type to mask.")
    
    elif file_type in ["image/png", "image/jpeg", "image/jpg"]:
        image = Image.open(uploaded_file)
        st.image(image, caption="Original Image", use_column_width=True)
        
        image_options = ["Emails", "Phone Numbers", "Account Numbers", "IFSC Codes"]
        selected_image_options = st.multiselect("Select data types to hide in the image:", image_options)
        
        if st.button("Blur Sensitive Data"):
            if selected_image_options:
                blurred_image = process_image(image, selected_image_options)
                st.image(blurred_image, caption="Image with Sensitive Data Blurred", use_column_width=True)
                buf = io.BytesIO()
                blurred_image.save(buf, format="PNG")
                st.download_button("Download Blurred Image", buf, "blurred_image.png")
            else:
                st.warning("Please select at least one data type to blur in the image.")
    
    elif file_type in ["video/mp4", "video/avi", "video/mov"]:
        st.video(uploaded_file)
        
        video_path = "uploaded_video.mp4"
        with open(video_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        video_options = ["Emails", "Phone Numbers", "Account Numbers", "IFSC Codes"]
        selected_video_options = st.multiselect("Select data types to mask in the video:", video_options)

        if st.button("Mask Sensitive Data"):
            if selected_video_options:
                frames = process_video(video_path, selected_video_options)
                clip = ImageSequenceClip(frames, fps=24)
                processed_video_path = "processed_video.mp4"
                clip.write_videofile(processed_video_path)
                
                with open(processed_video_path, "rb") as video_file:
                    st.download_button("Download Masked Video", video_file, file_name="masked_video.mp4")
            else:
                st.warning("Please select at least one data type to mask.")
    else:
        st.error("Unsupported file type.")
    ''')


# In[14]:

streamlit run app.py


