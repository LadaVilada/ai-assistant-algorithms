import logging
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
    def load_pdf(
            pdf_path: str,
            chunk_size: int = DEFAULT_CHUNK_SIZE,
            chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[Document]:
        """Load and split PDF document"""
        try:
            # Load PDF
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()
            
            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", " ", ""]
            )
            chunks = text_splitter.split_documents(pages)
            
            logging.info(f"Loaded PDF: {pdf_path}. Total chunks: {len(chunks)}")
            return chunks
            
        except FileNotFoundError as e:
            logging.error(f"PDF file not found at {pdf_path}: {e}")
            return []
        except Exception as e:
            logging.error(f"Error loading PDF {pdf_path}: {e}")
            return []

    @staticmethod
    def load_text(
            text_path: str,
            chunk_size: int = DEFAULT_CHUNK_SIZE,
            chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ) -> List[Document]:
        """Load and split text document"""
        try:
            # Load text file
            loader = TextLoader(text_path)
            documents = loader.load()

            # Split into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ".", " ", ""]
            )
            chunks = text_splitter.split_documents(documents)

            # Add source metadata if not present
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