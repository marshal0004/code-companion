import os
import hashlib
from pathlib import Path
from typing import List, Dict, Optional
import json

# Global flag for ChromaDB availability
CHROMADB_AVAILABLE = False

try:
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("ChromaDB not available. Semantic search will fall back to text search.")


class VectorStore:
    """Semantic code search using ChromaDB and sentence transformers"""
    
    def __init__(self, workspace_root: str = "/app"):
        self.workspace_root = Path(workspace_root)
        self.cache_dir = Path.home() / ".local/share/codecompanion/chromadb"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate workspace hash for collection name
        workspace_hash = hashlib.md5(str(self.workspace_root).encode()).hexdigest()[:16]
        self.collection_name = f"code_{workspace_hash}"
        
        self.client = None
        self.collection = None
        self.embedding_model = None
        
        if CHROMADB_AVAILABLE:
            try:
                self._initialize()
            except Exception as e:
                print(f"Failed to initialize ChromaDB: {e}")
    
    def _initialize(self):
        """Initialize ChromaDB and embedding model"""
        if not CHROMADB_AVAILABLE:
            return
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=str(self.cache_dir),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(self.collection_name)
        except:
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"workspace": str(self.workspace_root)}
            )
        
        # Initialize embedding model (lightweight and fast)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def is_available(self) -> bool:
        """Check if vector store is available"""
        return CHROMADB_AVAILABLE and self.client is not None
    
    def index_file(self, file_path: Path, content: str):
        """Index a single file with chunking"""
        if not self.is_available():
            return
        
        try:
            # Chunk the content (512 tokens with 50 token overlap)
            chunks = self._chunk_content(content, chunk_size=512, overlap=50)
            
            # Create document IDs and metadata
            rel_path = str(file_path.relative_to(self.workspace_root))
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{rel_path}::chunk_{i}"
                
                # Add to ChromaDB
                self.collection.add(
                    documents=[chunk],
                    metadatas=[{
                        "file": rel_path,
                        "chunk_index": i,
                        "file_type": file_path.suffix,
                    }],
                    ids=[doc_id]
                )
        except Exception as e:
            print(f"Failed to index {file_path}: {e}")
    
    def index_workspace(self, file_patterns: List[str] = None):
        """Index entire workspace"""
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        if file_patterns is None:
            file_patterns = ['*.py', '*.js', '*.ts', '*.jsx', '*.tsx', '*.go', '*.rs', '*.java', '*.cpp', '*.c', '*.h']
        
        indexed_count = 0
        
        # Find all code files
        for pattern in file_patterns:
            for file_path in self.workspace_root.rglob(pattern):
                # Skip common ignored directories
                if any(part in str(file_path) for part in ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'dist', 'build']):
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    if len(content) > 0:
                        self.index_file(file_path, content)
                        indexed_count += 1
                except Exception as e:
                    continue
        
        return {
            "success": True,
            "indexed_files": indexed_count,
            "collection": self.collection_name
        }
    
    def search(self, query: str, top_k: int = 5) -> Dict:
        """Semantic search across indexed code"""
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            # Search ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            search_results = []
            if results['documents'] and len(results['documents']) > 0:
                for i in range(len(results['documents'][0])):
                    search_results.append({
                        "file": results['metadatas'][0][i]['file'],
                        "chunk": results['documents'][0][i],
                        "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                        "chunk_index": results['metadatas'][0][i].get('chunk_index', 0)
                    })
            
            return {
                "success": True,
                "results": search_results,
                "count": len(search_results)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _chunk_content(self, content: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
        """Chunk content into smaller pieces with overlap"""
        words = content.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
            i += chunk_size - overlap
        
        return chunks
    
    def get_stats(self) -> Dict:
        """Get vector store statistics"""
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            count = self.collection.count()
            return {
                "success": True,
                "collection": self.collection_name,
                "document_count": count,
                "workspace": str(self.workspace_root)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def clear(self):
        """Clear all indexed data"""
        if not self.is_available():
            return {"success": False, "error": "ChromaDB not available"}
        
        try:
            self.client.delete_collection(self.collection_name)
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"workspace": str(self.workspace_root)}
            )
            return {"success": True, "message": "Index cleared"}
        except Exception as e:
            return {"success": False, "error": str(e)}
