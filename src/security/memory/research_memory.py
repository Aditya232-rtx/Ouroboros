import chromadb
import json
import os

class ResearchMemory:
    def __init__(self, persist_directory="./chroma_db"):
        # Initialize a local persistent vector database
        self.client = chromadb.PersistentClient(path=persist_directory)
        # Get or create a collection for our vulnerability intelligence
        self.collection = self.client.get_or_create_collection(name="cve_memory")

    def has_been_researched(self, cve_id: str) -> bool:
        """Checks if a CVE has already been processed."""
        results = self.collection.get(ids=[cve_id])
        return len(results['ids']) > 0

    def store_intelligence(self, cve_id: str, payload: dict):
        """Stores the validated JSON payload into vector memory."""
        json_str = json.dumps(payload)
        self.collection.upsert(
            documents=[json_str],
            metadatas=[{"source": "crawl4ai_research"}],
            ids=[cve_id]
        )
        print(f"[+] Memory updated: {cve_id} committed to ChromaDB.")
