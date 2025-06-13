import requests
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_community.agent_toolkits.load_tools import load_tools
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate

from src.medical_assistant.config import PERSIST_DIR, EMBEDDING_MODEL_NAME, LLM_MODEL_NAME, system_prompt


def create_medical_agent(api_key: str):
    """
    Initializes and returns the medical agent and vector store.
    """
    try:
        # Initialize LLM
        llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL_NAME,
            google_api_key=api_key,
            temperature=0.5,
        )

        # Initialize Embedding Model
        embedding_model = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)

        # Initialize Chroma Vector Store
        vectorstore = Chroma(
            persist_directory=PERSIST_DIR, embedding_function=embedding_model
        )

        # Load Tools (DuckDuckGo Search)
        tools = load_tools(["google-serper"])

        # Create React Agent
        agent_executor = agent = create_react_agent(model=llm,tools=tools,prompt=system_prompt)

        return agent_executor, vectorstore

    except Exception as e:
        print(f"Error creating agent: {e}")
        return None, None


def augment_prompt_with_rag(query: str, vectorstore: Chroma) -> str:
    """
    Performs RAG by searching the vector store and augmenting the prompt.
    """
    results = vectorstore.similarity_search(query, k=5)
    context = "\n----------------\n".join([doc.page_content for doc in results])
    if not context:
        return "There was no Local Context"
    return context


def serper_search(query: str, api_key: str):
    """
    Performs a search using the Serper API.
    """
    url = "https://google.serper.dev/search"
    payload = json.dumps({"q": query})
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status() 

        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error during Serper search: {e}")
        return "There was no Search Context due to an error."