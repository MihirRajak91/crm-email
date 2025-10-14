import os
import sys
import tempfile
import base64
import argparse
from pathlib import Path

from PIL import Image
from pdf2image import convert_from_path
import docx
from weasyprint import HTML, CSS
from openai import OpenAI
from crm.core.settings import get_settings
from crm.utils.logger import logger

settings = get_settings()

client = OpenAI(api_key=settings.OPENAI_API_KEY)

if not client.api_key:
    raise ValueError("OPENAI_API_KEY is not set in .env file.")

def docx_to_pdf(docx_path, pdf_path):
    """Convert DOCX to PDF via HTML using WeasyPrint (preserves basic layout)."""
    logger.info("Converting DOCX to PDF via HTML rendering", extra={
        "docx_path": str(docx_path),
        "pdf_path": str(pdf_path),
    })
    doc = docx.Document(docx_path)

    # Simple HTML conversion (supports basic formatting and tables)
    html_content = "<html><body style='font-family: sans-serif;'>"
    css = CSS(string='table { border-collapse: collapse; width: 100%; } td, th { border: 1px solid #ccc; padding: 8px; }')

    for element in doc.element.body:
        if element.tag.endswith('tbl'):  # Table
            table = docx.table.Table(element, doc)
            html_content += "<table>"
            for row in table.rows:
                html_content += "<tr>"
                for cell in row.cells:
                    tag = "th" if row == table.rows[0] else "td"
                    html_content += f"<{tag}>{cell.text}</{tag}>"
                html_content += "</tr>"
            html_content += "</table><br/>"
        elif element.tag.endswith('p'):  # Paragraph
            p = docx.text.paragraph.Paragraph(element, doc)
            html_content += f"<p>{p.text}</p>"

    html_content += "</body></html>"

    # Render HTML to PDF
    h = HTML(string=html_content)
    h.write_pdf(pdf_path, stylesheets=[css])
    logger.info("DOCX conversion complete", extra={
        "pdf_path": str(pdf_path),
    })


def document_to_images(doc_path):
    """Convert document (PDF or DOCX) to list of image paths (one per page)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        if doc_path.lower().endswith('.pdf'):
            pdf_path = tmpdir / "temp.pdf"
            os.link(doc_path, pdf_path)  # Copy file
        elif doc_path.lower().endswith('.docx'):
            pdf_path = tmpdir / "temp.pdf"
            docx_to_pdf(doc_path, pdf_path)
        else:
            raise ValueError("Unsupported format. Please provide a .pdf or .docx file.")

        # Convert PDF to images (high DPI for OCR/table clarity)
        logger.info("Converting PDF to images", extra={
            "source_path": str(pdf_path),
        })
        images = convert_from_path(pdf_path, dpi=200)  # High quality
        image_paths = []
        for i, img in enumerate(images):
            img_path = tmpdir / f"page_{i+1}.png"
            img.save(img_path, "PNG")
            image_paths.append(str(img_path))
            logger.debug("Page converted to image", extra={
                "page_number": i + 1,
                "image_path": str(img_path),
            })

        full_content = ""
        for i, img_path in enumerate(image_paths):
            logger.info("Processing page with OpenAI extraction", extra={
                "page_number": i + 1,
                "total_pages": len(image_paths),
                "image_path": img_path,
            })
            content = image_to_content(img_path)
            full_content += f"## Page {i+1}\n\n{content}\n\n---\n\n"

        return full_content


def image_to_content(image_path):
    """Send image to OpenAI GPT-4o and extract full content (text, tables, figures)."""
    with open(image_path, "rb") as image_file:
        encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

    logger.info("Sending page image to OpenAI", extra={
        "image_path": image_path,
        "model": settings.OPENAI_EXTRACT_CONTENT_MODEL,
    })

    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_EXTRACT_CONTENT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Analyze this document page thoroughly. Extract: \n"
                                "- All readable text (preserve structure: headings, lists, paragraphs)\n"
                                "- Tables: Represent them in Markdown format with proper alignment\n"
                                "- Figures/Images: Describe their content and purpose (e.g., 'Chart showing sales growth 2020–2023')\n"
                                "- Footnotes, captions, or side notes\n"
                                "Output in clean, structured Markdown. Use ## for headings, ``` for tables, and [Figure: ...] for images."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{encoded_image}",
                                "detail": "high"  # critical for tables and small text
                            }
                        }
                    ]
                }
            ],
            max_tokens=2000,
        )
        content = response.choices[0].message.content
        logger.debug("Received OpenAI extraction", extra={
            "image_path": image_path,
            "content_preview": content[:200] if isinstance(content, str) else None,
        })
        return content
    except Exception as e:
        logger.error("OpenAI extraction failed", exc_info=True, extra={
            "image_path": image_path,
        })
        return f"[ERROR processing {image_path}: {str(e)}]"


# def main():
#     parser = argparse.ArgumentParser(description="Convert PDF/DOCX pages to images and extract structured content (text, tables, images) using OpenAI GPT-4o.")
#     parser.add_argument("file_path", type=str, help="Path to the input PDF or DOCX file")
#     parser.add_argument("--output", type=str, default="extracted_content.md", help="Output Markdown file (default: extracted_content.md)")

#     args = parser.parse_args()

#     if not os.path.exists(args.file_path):
#         print(f"❌ File not found: {args.file_path}")
#         sys.exit(1)

#     try:
#         print(f"📄 Processing document: {args.file_path}")
#         image_paths = document_to_images(args.file_path)

#         full_content = f"# Extracted Content from: {os.path.basename(args.file_path)}\n\n"
#         full_content += f"*Processed on: {os.times().tm_gmtoff}*  \n"
#         full_content += f"*Model: GPT-4o (Vision)*  \n\n"

#         for i, img_path in enumerate(image_paths):
#             print(f"🖼️  Processing page {i+1}/{len(image_paths)}...")
#             content = image_to_content(img_path)
#             full_content += f"## Page {i+1}\n\n{content}\n\n---\n\n"

#         # Save result
#         with open(args.output, "w", encoding="utf-8") as f:
#             f.write(full_content)

#         print(f"\n✅ Extraction complete! Saved to: {args.output}")

#     except Exception as e:
#         print(f"❌ Error during processing: {e}")
#         sys.exit(1)


# if __name__ == "__main__":
#     main()
