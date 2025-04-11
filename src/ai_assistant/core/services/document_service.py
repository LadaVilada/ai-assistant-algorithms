import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import List, Dict, Callable, Tuple

import boto3
import fitz
from botocore.exceptions import NoCredentialsError
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# Load environment variables
load_dotenv()

def extract_keywords_simple(text: str, top_n=5):
    import re

    words = re.findall(r"\b[а-яА-Я]{4,}\b", text.lower())
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]

def upload_image_to_s3(file_path: str) -> dict:
    """Uploads image to S3 and returns both s3:// and https:// URLs"""

    S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')
    S3_FOLDER = os.getenv("S3_FOLDER")
    S3_REGION = os.getenv("S3_REGION")

    s3_client = boto3.client("s3")
    filename = os.path.basename(file_path)
    s3_key = f"{S3_FOLDER}/{filename}" # object_name: The name of the object in S3

    try:
        s3_client.upload_file(file_path, S3_BUCKET_NAME, s3_key)

        return {
            "s3_uri": f"s3://{S3_BUCKET_NAME}/{s3_key}",
            "http_url": f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{s3_key}"
        }

    except NoCredentialsError:
        logging.error("AWS credentials not found for S3 upload.")
        return {}
    except Exception as e:
        logging.error(f"Failed to upload {file_path} to S3: {e}")
        return {}

class DocumentService:
    """
    Advanced document loader with multiple file type support
    Responsibility : Load and preprocess documents.
    Content : Functions to read files, tokenize text, and prepare data for indexing.
    """
    
    # Define constants for default values
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 200
    
    # Define custom exceptions
    class UnsupportedFileTypeError(Exception):
        """Raised when the file type is not supported."""
        pass

    @staticmethod
    def clean_metadata(metadata: dict) -> dict:
        return {k: v for k, v in metadata.items() if v is not None}


    @staticmethod
    def load_pdf(pdf_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
        """
        Load and split a PDF document, extracting both text and images if present.
        Uses PyMuPDF (fitz) for image extraction.
        """
        try:
            import pytesseract
            from PIL import Image
            import io

            def extract_text_with_ocr(doc_page):
                pix = doc_page.get_pixmap(dpi=300)
                img_bytes = pix.tobytes("png")
                doc_image = Image.open(io.BytesIO(img_bytes))
                return pytesseract.image_to_string(doc_image, config='--oem 3 --psm 6 -l rus')

            # Open the PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            logging.info(f"Opened PDF: {pdf_path} with {doc.page_count} pages.")
            all_pages_text = []

            with tempfile.TemporaryDirectory() as output_dir:
                # Directory to save images
                output_dir = Path(output_dir)

                # Iterate through pages and extract text and images
                for page_num in range(doc.page_count):
                    page = doc[page_num]
                    # Extract text from page
                    page_text = page.get_text()
                    # If no text is found, use OCR
                    if not page_text.strip():
                        logging.warning(f"Page {page_num+1}: No text found. Using OCR...")
                        page_text = extract_text_with_ocr(page)
                        logging.info(f"Page {page_num+1}: OCR text length = {len(page_text)}")

                    # logging.warning(f"Page {page_num + 1}: Extracted text length = {len(page_text)}")
                    image_url = None

                    # Extract images from the page
                    image_list = page.get_images(full=True)
                    if image_list:
                        # Get the first image
                        xref = image_list[0][0]
                        base_image = doc.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]

                        # Create a unique filename
                        image_filename = f"{Path(pdf_path).stem}_page{page_num+1}_{uuid.uuid4().hex[:8]}.{image_ext}"
                        image_path = os.path.join(output_dir, image_filename)
                        with open(image_path, "wb") as img_file:
                            img_file.write(image_bytes)
                        # Upload image to S3
                        image_info = upload_image_to_s3(image_path)
                        if image_info:
                            s3_uri = image_info["s3_uri"]
                            # public_url = image_info["http_url"]
                            image_url = s3_uri
                        logging.info(f"Extracted image from page {page_num+1}: {image_url}")

                    # Create a Document with metadata including image_url if found
                    doc_metadata = {
                            "page": page_num + 1,
                            "source": os.path.basename(pdf_path),
                    }

                    # Add keywords only if they are a list of strings
                    keywords = extract_keywords_simple(page_text)
                    if isinstance(keywords, list) and all(isinstance(k, str) for k in keywords):
                        doc_metadata["keywords"] = keywords

                    # Add image_url only if it's a non-empty string
                    if isinstance(image_url, str) and image_url.strip():
                        doc_metadata["image_url"] = image_url

                    logging.info(f"📄 Page {page_num + 1} metadata: {doc_metadata}")

                    # Clean metadata to remove None values
                    cleaned_metadata = {k: v for k, v in doc_metadata.items() if v is not None}

                    all_pages_text.append(
                        Document(page_content=page_text, metadata=cleaned_metadata)
                    )

            # Now, use the RecursiveCharacterTextSplitter to further chunk the pages
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(all_pages_text)
            logging.info(f"Loaded PDF: {pdf_path}. Total chunks after splitting: {len(chunks)}")
            return chunks

        except FileNotFoundError as e:
            logging.error(f"PDF file not found at {pdf_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error loading PDF {pdf_path}: {e}")
            return []

    @staticmethod
    def load_text(text_path: str, chunk_size: int = DEFAULT_CHUNK_SIZE, chunk_overlap: int = DEFAULT_CHUNK_OVERLAP) -> List[Document]:
        """
        Load and split a text document.
        """
        try:
            from langchain_community.document_loaders import TextLoader

            loader = TextLoader(text_path)
            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)
            for chunk in chunks:
                if "source" not in chunk.metadata:
                    chunk.metadata["source"] = text_path
            logging.info(f"Loaded text file: {text_path}. Total chunks: {len(chunks)}")
            return chunks
        except FileNotFoundError as e:
            logging.error(f"Text file not found at {text_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error loading text file {text_path}: {e}")
            return []


    @classmethod
    def smart_load(
            cls,
            file_path: str,
            chunk_size: int = DEFAULT_CHUNK_SIZE,
            chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> Tuple[List[Document], bool]:
        """
        Intelligently load documents based on file extension
        
        Returns:
            Tuple containing:
            - List of document chunks
            - Boolean indicating success (True) or failure (False)
        """
        file_extension = Path(file_path).suffix.lower().lstrip('.')
        
        # Mapping of file extensions to loading methods
        loaders: Dict[str, Callable] = {
            'pdf': cls.load_pdf,
            'txt': cls.load_text,
            # TODO: Add more file type loaders as needed
        }
        
        # Select appropriate loader
        loader = loaders.get(file_extension)
        
        if loader:
            try:
                chunks = loader(file_path, chunk_size, chunk_overlap)
                return chunks, len(chunks) > 0
            except Exception as e:
                logging.error(f"Error in smart_load for {file_path}: {e}")
                return [], False
        else:
            logging.warning(f"Unsupported file type: {file_extension}")
            return [], False

    @classmethod
    def load_document(
            cls,
            file_path: str,
            chunk_size: int = DEFAULT_CHUNK_SIZE,
            chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[Document]:
        """
        Public method to load any supported document

        Args:
            file_path: Path to the document
            chunk_size: Size of each chunk
            chunk_overlap: Overlap between consecutive chunks

        Returns:
            List of document chunks
        """
        chunks, success = cls.smart_load(file_path, chunk_size, chunk_overlap)

        if not success:
            logging.warning(f"Failed to load document: {file_path}")
            return []

        return chunks