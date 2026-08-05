import os
import sys
import json
import sqlite3
import logging
import numpy as np
from deep_translator import GoogleTranslator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "master_registry.db")
VECTOR_INDEX_FILE = os.path.join(BASE_DIR, "vector_index.json")

class SimpleTFIDFEmbedding:
    """Lightweight vector embedding fallback generator."""
    def __init__(self):
        self.vocab = {}

    def fit_transform(self, texts):
        words = set()
        for t in texts:
            for w in t.lower().split():
                words.add(w)
        self.vocab = {w: i for i, w in enumerate(sorted(words))}
        
        vectors = []
        for t in texts:
            vec = np.zeros(len(self.vocab))
            for w in t.lower().split():
                if w in self.vocab:
                    vec[self.vocab[w]] += 1.0
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec.tolist())
        return vectors

    def transform_single(self, text):
        vec = np.zeros(len(self.vocab))
        for w in text.lower().split():
            if w in self.vocab:
                vec[self.vocab[w]] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

class SemanticVectorSearchEngine:
    """Indexes video metadata and provides cosine-similarity semantic vector queries."""

    def __init__(self):
        self.embedder = SimpleTFIDFEmbedding()
        self.index_data = []

    def build_index_from_database(self):
        if not os.path.exists(DB_PATH):
            logging.warning("[!] Database not found. Skipping vector indexing.")
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT filepath, category, filename FROM assets")
        records = cursor.fetchall()
        conn.close()

        if not records:
            logging.info("[*] No database records found to index.")
            return

        texts = [f"{r[2]} {r[1]}" for r in records]
        vectors = self.embedder.fit_transform(texts)

        self.index_data = []
        for i, r in enumerate(records):
            self.index_data.append({
                "filepath": r[0],
                "category": r[1],
                "filename": r[2],
                "vector": vectors[i]
            })

        with open(VECTOR_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(self.index_data, f, indent=4)

        logging.info(f"[+] Successfully built semantic vector index across {len(self.index_data)} assets.")

    def query_top_k(self, query_text, top_k=3):
        if not self.index_data:
            if os.path.exists(VECTOR_INDEX_FILE):
                with open(VECTOR_INDEX_FILE, "r", encoding="utf-8") as f:
                    self.index_data = json.load(f)
            else:
                self.build_index_from_database()

        if not self.index_data:
            return []

        query_vec = np.array(self.embedder.transform_single(query_text))
        results = []

        for item in self.index_data:
            doc_vec = np.array(item["vector"])
            if len(doc_vec) == len(query_vec) and np.linalg.norm(query_vec) > 0 and np.linalg.norm(doc_vec) > 0:
                score = float(np.dot(query_vec, doc_vec))
            else:
                score = 0.0
            results.append((score, item))

        results.sort(key=lambda x: x[0], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    logging.info("[*] Testing Semantic Vector Search Engine...")
    engine = SemanticVectorSearchEngine()
    engine.build_index_from_database()
    top_matches = engine.query_top_k("audit analysis report", top_k=2)
    logging.info(f"[+] Query Test Results: {top_matches}")