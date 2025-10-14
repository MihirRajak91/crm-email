import os
import re
import requests
from typing import Dict, Optional
from urllib.parse import urlparse
from crm.utils.logger import logger

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
rag_dir = os.path.join(BASE_DIR,"..","..","rag_documents")


class MetadataProcessor:
    """
    Description: Service for processing and downloading different file types (PDF, DOCX, MP4, Zeta) with local and remote storage support
    
    args:
        output_dir (str): Directory where files will be saved, defaults to rag_documents directory
    
    returns:
        MetadataProcessor: Instance for handling file downloads and processing across multiple file formats
    """
    
    def __init__(self, base_url: str = 'http://192.168.1.68:9011/media', output_dir: str =rag_dir):
        """
        Description: Initialize the MetadataProcessor with base URL and output directory configuration
        
        args:
            base_url (str): Base URL for remote media file access
            output_dir (str): Local directory path for saving downloaded files
        
        returns:
            None
        """
        self.base_url = base_url
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def download_file(self, file_info: Dict, expected_type: str) -> Optional[str]:
        """
        Generic method to download and save files.
        
        Args:
            file_info (dict): Metadata of the file to be processed
            expected_type (str): Expected file type (pdf/docx)
        
        Returns:
            str: Path to the saved file
        """
        file_url: str = file_info.file_path
        file_id: str = file_info.resource_id

        # Use the original filename from the event data, with proper extension
        original_filename = getattr(file_info, 'file_name', '')
        
        # Derive a safe extension. If URL, strip query/fragment; fallback to expected type
        parsed = urlparse(file_url)
        candidate_path = parsed.path if parsed.scheme in ("http", "https") else file_url
        derived_ext = os.path.splitext(candidate_path)[-1]
        ext = derived_ext if derived_ext and derived_ext.lower() in (f".{expected_type}", ".pdf", ".docx", ".mp4", ".html") else f".{expected_type}"
        
        # Use original filename if available, otherwise fallback to resource_id
        if original_filename:
            # Clean the filename to remove any invalid characters
            clean_filename = re.sub(r'[<>:"/\\|?*]', '_', original_filename)
            # Ensure the filename has the correct extension
            if not clean_filename.lower().endswith(ext.lower()):
                clean_filename = clean_filename + ext
            file_name = clean_filename
        else:
            file_name = f"{file_id}{ext}"
        
        # If flag is "local", treat file path as direct
        # if str(getattr(file_info, "flag", "")).lower() == "local":
        #     print(f'Local file path: {file_url}')
        #     return file_url
        
        # Prefer absolute URL directly; only prefix base_url for relative paths
        url = file_url if file_url.startswith(("http://", "https://")) else f"{self.base_url}/{file_url}"
        
        file_path: str = os.path.join(self.output_dir, file_name)
        
        try:
            # Define headers for browser-like behavior
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                ),
                "Accept": "application/pdf,application/octet-stream,*/*",
                "Referer": url
            }

            response: requests.Response = requests.get(url,headers=headers, timeout=10)
            
            logger.info(f"Status Code: {response.status_code}")
            logger.info(f"Content-Type: {response.headers.get('Content-Type')}")
            logger.info(f"Content-Length: {response.headers.get('Content-Length')}")
            
            if response.status_code == 200:
                content_type: str = response.headers.get("Content-Type", "").lower()
                if expected_type in content_type or ext.lower() == f".{expected_type}":
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    file_size: int = os.path.getsize(file_path)
                else:
                    raise ValueError(f"Unsupported file type for {file_id}: {content_type}")
            else:
                logger.warning(f"Failed to fetch file. Status Code: {response.status_code}")
                logger.debug(f"Response Text: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except ValueError as e:
            logger.error(str(e))
            return None
        
        return file_path

    def process_pdf(self, file_info: Dict) -> Optional[str]:
        """Process PDF files"""
        return self.download_file(file_info, "pdf")

    def process_docx(self, file_info: Dict) -> Optional[str]:
        """Process DOCX files"""
        return self.download_file(file_info, "docx")
    
    def process_zeta(self, file_info: Dict) -> Optional[str]:
        """
        Process Zeta files (HTML summaries).
        
        Args:
            file_info (dict): Metadata of the file to be processed
        
        Returns:
            str: Path to the saved HTML file
        """
        file_id: str = file_info.resource_id
        file_summary: str = file_info.summary if getattr(file_info, 'summary', None) else ""
        remote_path: str = getattr(file_info, 'file_path', '') or ''
        summary_preview = file_summary.replace('\n', ' ').replace('\r', ' ')[:50] + "..." if len(file_summary) > 100 else file_summary.replace('\n', ' ').replace('\r', ' ')
        logger.info(f"File summary: {summary_preview}")
        summary_html: Optional[str] = None
        if isinstance(file_summary, str) and file_summary.strip():
            # Use provided summary
            summary_html = file_summary.strip()
            if not summary_html.lower().startswith("<html"):
                summary_html = f"<html><body>{summary_html}</body></html>"
        else:
            # Try to download HTML/Zeta from remote path as a fallback
            if isinstance(remote_path, str) and remote_path.startswith(("http://", "https://")):
                try:
                    headers = {
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
                        ),
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Referer": remote_path,
                    }
                    resp = requests.get(remote_path, headers=headers, timeout=10, verify=False)
                    if resp.status_code == 200:
                        text = resp.text or ""
                        if text.strip():
                            summary_html = text
                    else:
                        logger.warning(f"Failed to fetch zeta HTML from URL (status={resp.status_code}).")
                except Exception as e:
                    logger.error(f"Error fetching zeta HTML from URL: {e}")

            if not summary_html:
                logger.warning(f"No summary/remote HTML for resource_id={file_id}. Skipping.")
                return None

        html_file_name: str = f"{file_id}.html"
        html_file_path: str = os.path.join(self.output_dir, html_file_name)
        
        try:
            with open(html_file_path, 'w', encoding='utf-8') as html_file:
                html_file.write(summary_html)
            logger.info(f"HTML file saved: {html_file_name}")
        except Exception as e:
            logger.error(f"Failed to save HTML file {getattr(file_info, 'file_name', '')} -> {html_file_name}: {e}")
            return None
        return html_file_path