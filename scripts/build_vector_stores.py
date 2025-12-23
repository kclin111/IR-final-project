"""
Script to build vector stores from preprocessed data
Run this before starting the application for the first time
"""
import sys
from pathlib import Path

# Add project root to path FIRST
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Then import from app
from app.utils.vector_store import VectorStoreBuilder
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Build ChromaDB vector stores for laws and cases"
    )
    parser.add_argument(
        "--law-csv",
        type=str,
        default="data/cleaned_道路交通管理處罰條例.csv",
        help="Path to cleaned law CSV file"
    )
    parser.add_argument(
        "--case-jsonl",
        type=str,
        default="data/traffic_cases_chunks.jsonl",
        help="Path to traffic cases chunks JSONL file"
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default="data/chroma_db",
        help="Directory to persist ChromaDB"
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild collections (delete existing first)"
    )

    args = parser.parse_args()

    print("\n" + "="*60)
    print("  Building Vector Stores for Traffic Law Retrieval System")
    print("="*60 + "\n")

    # Initialize builder
    builder = VectorStoreBuilder(persist_directory=args.persist_dir)

    # Rebuild if requested
    if args.rebuild:
        print("Deleting existing collections...")
        builder.delete_collection("law_knowledge_points")
        builder.delete_collection("case_applications")
        print()

    # Build law collection
    print("Building law knowledge points collection...")
    print(f"   Source: {args.law_csv}")
    law_collection = builder.build_law_collection(
        csv_path=args.law_csv,
        collection_name="law_knowledge_points"
    )
    print()

    # Build case collection
    print("Building case applications collection...")
    print(f"   Source: {args.case_jsonl}")
    case_collection = builder.build_case_collection(
        jsonl_path=args.case_jsonl,
        collection_name="case_applications"
    )
    print()

    # List all collections
    collections = builder.list_collections()
    print("Vector stores built successfully!")
    print(f"   Persist directory: {args.persist_dir}")
    print(f"   Collections: {', '.join(collections)}")
    print()

    # Verify collections
    print("Verifying collections...")
    law_count = law_collection._collection.count()
    case_count = case_collection._collection.count()

    print(f"   ✓ Law knowledge points: {law_count} documents")
    print(f"   ✓ Case applications: {case_count} chunks")
    print()

    print("="*60)
    print("  Setup Complete! You can now start the application.")
    print("  Run: python -m app.main")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
