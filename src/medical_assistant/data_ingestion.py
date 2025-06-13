import os
import shutil
import pandas as pd
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from src.medical_assistant.config import DATA_PATH, PERSIST_DIR, EMBEDDING_MODEL_NAME

def ingest_main():
    """
    Main function to ingest data, create embeddings, and persist the vector store.
    It now checks for existing documents using similarity_search before adding.
    """
    print("--- Starting Data Ingestion ---")

    # Check data file exists using isfile to avoid mocking conflicts
    if not os.path.isfile(DATA_PATH):
        raise FileNotFoundError(
            f"Error: Data file not found at '{DATA_PATH}'. Please ensure it's in the project root."
        )
    print(f"Found data file: '{DATA_PATH}'")

    try:
        df = pd.read_excel(DATA_PATH)
        if "Sentence" not in df.columns:
            raise ValueError(f"Column 'Sentence' not found in '{DATA_PATH}'. Please ensure the column name is correct.")
        sentences = df["Sentence"].dropna().tolist()
        if not sentences:
            print(f"Warning: No valid sentences found in the 'Sentence' column of '{DATA_PATH}'. Exiting.")
            return
        print(f"Successfully loaded {len(sentences)} sentences from the 'Sentence' column in '{DATA_PATH}'.")
    except Exception as e:
        print(f"Error loading or processing Excel file '{DATA_PATH}': {e}")
        return

    all_new_documents = [Document(page_content=sentence) for sentence in sentences]

    print(f"Loading embedding model: '{EMBEDDING_MODEL_NAME}'...")
    print("(This may take a few minutes and download data on the first run if not cached)")
    try:
        embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    except Exception as e:
        print(f"Error initializing embedding model: {e}")
        print("Please check your internet connection")
        return

    vectorstore = None
    documents_to_add = []

    # Check for existing Chroma DB based on directory existence and file names
    chroma_db_exists = os.path.exists(PERSIST_DIR) and any(f.startswith('chroma') for f in os.listdir(PERSIST_DIR))

    if chroma_db_exists:
        print(f"Found existing vector store at '{PERSIST_DIR}'. Attempting to load...")
        try:
            vectorstore = Chroma(
                persist_directory=PERSIST_DIR,
                embedding_function=embedding_model
            )
            print("ChromaDB loaded successfully.")

            print("Checking for existing documents in ChromaDB using similarity search...")
            for doc in all_new_documents:
                existing_docs = vectorstore.similarity_search(doc.page_content, k=1)

                if not (existing_docs and existing_docs[0].page_content == doc.page_content):
                    documents_to_add.append(doc)

            if not documents_to_add:
                print("No new unique documents from the data file found to add. ChromaDB is already up to date.")
            else:
                print(f"Identified {len(documents_to_add)} new unique documents to add to the existing database.")

        except Exception as e:
            print(f"Error loading existing Chroma vector store from '{PERSIST_DIR}': {e}")
            print("The existing vector store might be corrupted or incompatible. Attempting to create a new one.")
            if os.path.exists(PERSIST_DIR):
                print(f"Removing potentially corrupted vector store at '{PERSIST_DIR}'...")
                shutil.rmtree(PERSIST_DIR)
            vectorstore = None

    if vectorstore is None:
        print(f"Creating a new vector store at '{PERSIST_DIR}'...")
        try:
            vectorstore = Chroma.from_documents(
                documents=all_new_documents,
                embedding=embedding_model,
                persist_directory=PERSIST_DIR
            )
            print(f"Successfully created a new vector store with {len(all_new_documents)} documents.")
        except Exception as e:
            print(f"Error creating Chroma vector store: {e}")
            return
    elif documents_to_add:
        try:
            print(f"Adding {len(documents_to_add)} new unique documents to the existing vector store...")
            vectorstore.add_documents(documents=documents_to_add)
            print("New documents successfully added.")
        except Exception as e:
            print(f"Error adding new documents to existing Chroma vector store: {e}")
            return

    print("--- Data Ingestion Complete! ---")
    print(f"Vector store is ready at '{PERSIST_DIR}'.")

if __name__ == "__main__":
    ingest_main()
