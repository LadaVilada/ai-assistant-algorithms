import logging
import os
import uuid

import fitz
from pathlib import Path
from typing import List, Dict, Callable, Tuple

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


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
            # Open the PDF with PyMuPDF
            doc = fitz.open(pdf_path)
            logging.info(f"Opened PDF: {pdf_path} with {doc.page_count} pages.")

            all_pages_text = []
            # Directory to save images
            output_dir = "extracted_images"
            os.makedirs(output_dir, exist_ok=True)

            # Iterate through pages and extract text and images
            for page_num in range(doc.page_count):
                page = doc[page_num]
                # Extract text from page
                page_text = page.get_text()
                # Initialize image_url as a fallback
                # image_url = None
                # Set fallback image (mock) in case no real image is found
                image_url = "file:///Users/ladavilada/Desktop/Screenshot%202025-03-30%20at%209.59.49%E2%80%AFAM.png"

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
                    image_url = f"file://{image_path}"
                    # image_url = image_path  # For production, replace with a URL after uploading
                    logging.info(f"Extracted image from page {page_num+1}: {image_url}")

                # Create a Document with metadata including image_url if found
                # Note: We use a temporary Document object with page_content as page text.
                doc_metadata = {
                    "page": page_num + 1,
                    "source": os.path.basename(pdf_path),
                    "image_url": image_url,
                }

                # Clean None values (though now we guarantee image_url is always a string)
                cleaned_metadata = {k: v for k, v in doc_metadata.items() if v is not None}
                all_pages_text.append(Document(page_content=page_text, metadata=cleaned_metadata))


                # all_pages_text.append(Document(page_content=page_text, metadata=doc_metadata))

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
            # Add more file type loaders as needed
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