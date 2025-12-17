import base64
import io
import mimetypes
from pathlib import Path
from pdf2image import convert_from_path
import pymupdf

from platformdirs import user_config_path

IMAGE_TYPE_PNG = "image/png"
IMAGE_TYPE_PDF = "application/pdf"
ALLOWED_IMAGE_TYPES = {IMAGE_TYPE_PNG, "image/jpeg", "image/jpg", "image/webp"}


def read_pdf(path: str, min_chars = 50, dpi = 200, force_vision=False):
    """Return a list of OpenAI-ready content dicts"""
    mime = detect_file_type(path)
    
    content_list = []
    
    if mime in ALLOWED_IMAGE_TYPES:
        b64_url = image_file_to_base64(path)
        content_list.append({
            "type": "image_url",
            "image_url": {"url": b64_url}
        })
        return content_list
    
    if mime == IMAGE_TYPE_PDF:
        text = extract_text_from_pdf(path)
        if len(text) > min_chars and not force_vision:
            # PDF has extractable text → input_text
            content_list.append({
                "type": "text",
                "text": text
            })
        else:
            # No text → convert pages to images
            images = xconvert_from_path(path, dpi=dpi)
            for image in images:
                buf = io.BytesIO()
                image.save(buf, format='png')
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": image_bytes_to_base64(buf.getvalue(), IMAGE_TYPE_PNG)}
                })
        return content_list
    
    raise ValueError(f"Unsupported file type or cannot decode: {path}")

def detect_file_type(file_path):
    """Return MIME type"""
    mime, _ = mimetypes.guess_type(file_path)
    return mime

def extract_text_from_pdf(path):
    """Try to extract text from a PDF"""
    doc = pymupdf.open(path)
    text = '\n'.join(
        page.get_text()
        for page in doc
    )
    return text

def xconvert_from_path(path, dpi=200):
    """Try to extract text from a PDF"""
    from PIL import Image
    doc = pymupdf.open(path)
    images = []
    
    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        images.append(img)

    return images


def image_file_to_base64(path: Path, mime: str = None):
    if mime is None:
        mime = detect_file_type(path)
    return image_bytes_to_base64(path.read_bytes(), mime)

def image_bytes_to_base64(image_bytes, mime):
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:{mime};base64,{b64}"