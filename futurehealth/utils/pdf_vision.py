from importlib import import_module


def _require_pdf_vision_dependencies():
    try:
        pymupdf = import_module('pymupdf')
        image_module = import_module('PIL.Image')
    except ModuleNotFoundError as exc:
        raise SystemExit('Vision support requires optional dependencies. Install future-healthcare[vision].') from exc
    return pymupdf, image_module


def xconvert_from_path(path, dpi=200):
    """Convert PDF pages to compressed images."""
    pymupdf, image_module = _require_pdf_vision_dependencies()

    doc = pymupdf.open(path)
    images = []

    for page in doc:
        pix = page.get_pixmap(dpi=dpi)
        img = image_module.frombytes('RGB', [pix.width, pix.height], pix.samples)
        # Resize to maximum 1024x1024 to reduce size - phone photos will be huge...
        max_size = 1024
        if img.width > max_size or img.height > max_size:
            img.thumbnail((max_size, max_size), image_module.Resampling.LANCZOS)

        images.append(img)

    return images
