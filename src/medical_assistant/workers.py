import os
from PySide6.QtCore import QThread, Signal
from unstructured.partition.auto import partition
from langchain_core.messages import AIMessage, HumanMessage,ToolMessage
from langchain_chroma import Chroma

from src.medical_assistant.agent import (
    create_medical_agent,
    augment_prompt_with_rag,
    serper_search
)
from src.medical_assistant.config import disclaimer

class AgentInitializationWorker(QThread):
    """Worker to initialize the medical agent in the background."""
    agent_initialized = Signal(bool, object, object)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            print("AgentInitializationWorker: Starting agent creation...")
            agent_executor, vector_store = create_medical_agent(self.api_key)
            if agent_executor and vector_store:
                print("AgentInitializationWorker: Agent created successfully.")
                self.agent_initialized.emit(True, agent_executor, vector_store)
            else:
                print("AgentInitializationWorker: Agent creation returned None.")
                self.agent_initialized.emit(False, None, None)
        except Exception as e:
            print(f"AgentInitializationWorker: Error during agent initialization: {e}")
            self.agent_initialized.emit(False, None, None)

class ChromaDBIngestionWorker(QThread):
    """Worker to process and ingest single documents into ChromaDB from the UI."""
    finished = Signal(bool, str)

    def __init__(self, document_path: str, vectorstore: Chroma):
        super().__init__()
        self.document_path = document_path
        self.vectorstore = vectorstore

    def run(self):
        try:
            if not os.path.exists(self.document_path):
                self.finished.emit(False, f"File not found: {self.document_path}")
                return

            print("Starting document partitioning...")
            elements = partition(self.document_path)
            texts_from_doc = [el.text for el in elements if hasattr(el, 'text') and el.text.strip()]
            print(f"Partitioned into {len(texts_from_doc)} text elements.")
            
            new_texts_to_add = []
            for text in texts_from_doc:
                existing_docs = self.vectorstore.similarity_search(text, k=1)
                if not (existing_docs and existing_docs[0].page_content == text):
                    new_texts_to_add.append(text)
            
            if new_texts_to_add:
                self.vectorstore.add_texts(texts=new_texts_to_add)
                message = f"Added {len(new_texts_to_add)} new sections to the knowledge base."
                print(message)
                self.finished.emit(True, message)
            else:
                message = "Content already exists in the knowledge base."
                print(message)
                self.finished.emit(True, message)

        except Exception as e:
            error_message = f"An error occurred during ingestion: {e}"
            print(error_message)
            self.finished.emit(False, error_message)

class MedicalAgentWorker(QThread):
    """Worker to process user query with the medical agent."""
    response_generated = Signal(str)

    def __init__(self, agent_executor, vector_store: Chroma,serper_apiKeyInput:str, query: str, chat_history: list):
        super().__init__()
        self.agent_executor = agent_executor
        self.vector_store = vector_store
        self.serper_apiKeyInput = serper_apiKeyInput
        self.query = query
        self.chat_history = chat_history

    def run(self):
        try:
            local_context = augment_prompt_with_rag(self.query, self.vector_store)
            serper_context = serper_search(self.query, self.serper_apiKeyInput)
            
            augmented_prompt = (
                f"Please answer the user's query based on your instructions. "
                f"Here is some context retrieved from a local knowledge base that might be relevant:\n"
                f"--- Local Context ---\n{local_context}\n--- End Local Context ---\n\n"
                f"Here is some context retrieved from a search that might be relevant:\n"
                f"--- Search Context ---\n{serper_context}\n--- End Search Context ---\n\n"
                f"<User Query>User Query: **\"{self.query}\"**</User Query>"
            )

            response = self.agent_executor.invoke(
                {"messages": [*self.chat_history,HumanMessage(content=augmented_prompt)]}
            )
            final_content = response["messages"][-1].content
            final_response = f"{disclaimer}\n\n{final_content}"
            self.response_generated.emit(final_response)

        except Exception as e:
            error_message = f"Error during AI processing: {e}"
            print(error_message)
            self.response_generated.emit(error_message)