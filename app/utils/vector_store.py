"""
Vector store builder for laws and cases
Builds ChromaDB collections from preprocessed data
"""
import csv
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.config import settings


class VectorStoreBuilder:
    """Build and manage vector stores for laws and cases"""

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        embedding_model: str = None
    ):
        """
        Initialize vector store builder

        Args:
            persist_directory: Directory to persist ChromaDB
            embedding_model: Embedding model name
        """
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self.embedding_provider = settings.EMBEDDING_PROVIDER
        
        # Initialize embeddings based on provider
        if self.embedding_provider == "huggingface":
            self.embeddings = HuggingFaceEmbeddings(
                model_name=self.embedding_model,
                model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU available
                encode_kwargs={'normalize_embeddings': True}  # BGE models need normalization
            )
        else:
            self.embeddings = OpenAIEmbeddings(
                model=self.embedding_model,
                openai_api_key=settings.OPENAI_API_KEY
            )

        # Ensure persist directory exists
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

    def build_law_collection(
        self,
        csv_path: str,
        collection_name: str = "law_knowledge_points"
    ) -> Chroma:
        """
        Build law knowledge points collection from CSV

        Args:
            csv_path: Path to cleaned law CSV file
            collection_name: Name of the collection

        Returns:
            Chroma vector store instance
        """
        print(f"Building law collection from {csv_path}...")

        laws = []
        texts = []
        metadatas = []
        ids = []

        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip BOM if present
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]

            reader = csv.DictReader(content.splitlines())

            for idx, row in enumerate(reader):
                # Document text: 條號 + 條文內容
                doc_text = f"{row['條號']} {row['條文內容']}"

                # Metadata
                metadata = {
                    "cited_law": row['cited_law'],
                    "法規名稱": row['法規名稱'],
                    "章名": row['章名'],
                    "節名": row['節名'],
                    "條號": row['條號'],
                    "條文內容": row['條文內容'],
                    "source_type": "law"
                }

                texts.append(doc_text)
                metadatas.append(metadata)
                ids.append(f"law_{idx}")

        print(f"Creating {len(texts)} law documents...")

        # Create Chroma collection
        law_collection = Chroma.from_texts(
            texts=texts,
            metadatas=metadatas,
            ids=ids,
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )

        print(f"✓ Law collection created with {len(texts)} documents")
        return law_collection

    def build_case_collection(
        self,
        jsonl_path: str,
        collection_name: str = "case_applications",
        batch_size: int = 100
    ) -> Chroma:
        """
        Build case applications collection from JSONL with batch processing

        Args:
            jsonl_path: Path to traffic cases chunks JSONL file
            collection_name: Name of the collection
            batch_size: Number of chunks to process per batch

        Returns:
            Chroma vector store instance
        """
        print(f"Building case collection from {jsonl_path}...")

        texts = []
        metadatas = []
        ids = []
        chunk_count = 0

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                case = json.loads(line)

                for chunk in case['chunks']:
                    # Document text: chunk text only
                    doc_text = chunk['text']

                    # Infer chunk type from text prefix
                    chunk_type = self._infer_chunk_type(chunk['text'])

                    # Metadata
                    metadata = {
                        "case_id": case['id'],
                        "chunk_id": chunk['chunk_id'],
                        "JID": case['JID'],
                        "JYEAR": case['JYEAR'],
                        "JCASE": case['JCASE'],
                        "JNO": case['JNO'],
                        "JDATE": case['JDATE'],
                        "JTITLE": case['JTITLE'],
                        "court": case['court'],
                        "JPDF": case['JPDF'],
                        "cited_traffic_laws": json.dumps(
                            case.get('cited_traffic_laws', []),
                            ensure_ascii=False
                        ),  # Store as JSON string
                        "chunk_text": chunk['text'],
                        "chunk_type": chunk_type or "unknown",
                        "source_type": "case"
                    }

                    texts.append(doc_text)
                    metadatas.append(metadata)
                    ids.append(chunk['chunk_id'])
                    chunk_count += 1

        print(f"Processing {chunk_count} case chunks in batches of {batch_size}...")

        # Create collection first with initial batch
        first_batch_size = min(batch_size, len(texts))
        case_collection = Chroma.from_texts(
            texts=texts[:first_batch_size],
            metadatas=metadatas[:first_batch_size],
            ids=ids[:first_batch_size],
            embedding=self.embeddings,
            collection_name=collection_name,
            persist_directory=self.persist_directory
        )

        print(f"  ✓ Created collection with first {first_batch_size} chunks")

        # Add remaining chunks in batches
        for i in range(first_batch_size, len(texts), batch_size):
            batch_end = min(i + batch_size, len(texts))
            batch_texts = texts[i:batch_end]
            batch_metadatas = metadatas[i:batch_end]
            batch_ids = ids[i:batch_end]

            case_collection.add_texts(
                texts=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids
            )

            print(f"  ✓ Added batch {i//batch_size + 1}: {len(batch_texts)} chunks (Total: {batch_end}/{chunk_count})")

        print(f"✓ Case collection created with {chunk_count} chunks")
        return case_collection

    def _infer_chunk_type(self, text: str) -> Optional[str]:
        """
        Infer chunk type from text prefix

        Args:
            text: Chunk text

        Returns:
            Chunk type or None
        """
        chunk_types = [
            '理由要領', '主文', '事實', '理由',
            '本院之判斷', '程序', '得心證之'
        ]

        for chunk_type in chunk_types:
            if text.startswith(chunk_type):
                return chunk_type.rstrip('：')

        return None

    def load_law_collection(
        self,
        collection_name: str = "law_knowledge_points"
    ) -> Chroma:
        """
        Load existing law collection

        Args:
            collection_name: Name of the collection

        Returns:
            Chroma vector store instance
        """
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def load_case_collection(
        self,
        collection_name: str = "case_applications"
    ) -> Chroma:
        """
        Load existing case collection

        Args:
            collection_name: Name of the collection

        Returns:
            Chroma vector store instance
        """
        return Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.persist_directory
        )

    def delete_collection(self, collection_name: str):
        """
        Delete a collection

        Args:
            collection_name: Name of the collection to delete
        """
        client = chromadb.PersistentClient(path=self.persist_directory)
        try:
            client.delete_collection(name=collection_name)
            print(f"✓ Deleted collection: {collection_name}")
        except Exception as e:
            print(f"✗ Failed to delete collection {collection_name}: {e}")

    def list_collections(self) -> List[str]:
        """
        List all collections

        Returns:
            List of collection names
        """
        client = chromadb.PersistentClient(path=self.persist_directory)
        collections = client.list_collections()
        return [col.name for col in collections]
