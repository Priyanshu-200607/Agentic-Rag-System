"""
Document Processor Facade.
Re-exports process_file, determine_document_access_level, and create_parent_child_chunks.
"""

from core.document_processor import process_file, determine_document_access_level
from core.chunking import create_parent_child_chunks
