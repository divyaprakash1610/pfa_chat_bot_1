# modules/rag.py
import os
import faiss
import pickle
from sentence_transformers import SentenceTransformer
import numpy as np

class RAGRetriever:
    def __init__(
        self,
        docs_path="data/documents_txt/",
        index_path="data/embeddings.faiss",
        embed_path="data/docs.pkl",
        chunk_size=1000  # max chars per chunk
    ):
        self.docs = []
        self.texts = []
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.index_path = index_path
        self.embed_path = embed_path
        self.index = None
        self.chunk_size = chunk_size

        # Load cached FAISS index + docs if available
        if os.path.exists(index_path) and os.path.exists(embed_path):
            self.index = faiss.read_index(index_path)
            with open(embed_path, "rb") as f:
                self.docs = pickle.load(f)
                self.texts = [doc["content"] for doc in self.docs]
            print("✅ Loaded cached FAISS index and embeddings")
        else:
            self._load_docs(docs_path)
            # Save index and docs for future runs
            os.makedirs(os.path.dirname(embed_path), exist_ok=True)
            faiss.write_index(self.index, index_path)
            with open(embed_path, "wb") as f:
                pickle.dump(self.docs, f)
            print("✅ Created new FAISS index and saved embeddings")

    def _chunk_text(self, text):
        """Split text into chunks of max chunk_size characters"""
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + self.chunk_size])
            start += self.chunk_size
        return chunks

    def _load_docs(self, path):
        if not os.path.exists(path):
            raise ValueError(f"Document path does not exist: {path}")

        for fname in os.listdir(path):
            if fname.endswith(".txt"):
                file_path = os.path.join(path, fname)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    # Split into chunks
                    for chunk in self._chunk_text(content):
                        self.docs.append({"name": fname, "content": chunk})
                        self.texts.append(chunk)

        if not self.texts:
            raise ValueError("No valid text files found to create embeddings!")

        # Create embeddings
        embeddings = self.model.encode(self.texts, convert_to_numpy=True)

        # Ensure 2D
        if len(embeddings.shape) == 1:
            embeddings = embeddings.reshape(1, -1)

        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dim)
        self.index.add(embeddings)

    def retrieve(self, query, top_k=2):
        """Retrieve top_k relevant chunks for a query"""
        if not self.index or not self.docs:
            return []

        q_emb = self.model.encode([query], convert_to_numpy=True)
        D, I = self.index.search(q_emb, top_k)
        results = [self.docs[i] for i in I[0] if i < len(self.docs)]
        return results
