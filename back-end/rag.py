# import chromadb
# from chromadb.utils import embedding_functions
# from openai import OpenAI
# from dotenv import load_dotenv
# from fill_db import fill_db
# import json
# import os

# load_dotenv()

# DATA_PATH = "./data/hospital_data.pdf"
# CHROMA_PATH = "./chroma_db"

# # Initialize ChromaDB client
# chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)

# # Set up the same embedding function that was used for indexing
# openai_ef = embedding_functions.OpenAIEmbeddingFunction(
#     api_key=os.environ.get("OPENAI_API_KEY"),
#     model_name="text-embedding-3-small"
# )

# def rag(question, chroma_path=CHROMA_PATH, collection_name="hospital_db"):
#     # Initialize ChromaDB client
#     chroma_client = chromadb.PersistentClient(path=chroma_path)
    
#     # Set up the same embedding function that was used for indexing
#     openai_ef = embedding_functions.OpenAIEmbeddingFunction(
#         api_key=os.environ.get("OPENAI_API_KEY"),
#         model_name="text-embedding-3-small"
#     )
    
#     try:
#         # First try to get the collection with the embedding function
#         collection = chroma_client.get_collection(name=collection_name, embedding_function=openai_ef)
#         using_embeddings = True
#     except ValueError as e:
#         # If there's a mismatch, fall back to the default embedding function
#         print(f"Note: {e}")
#         print("Falling back to the default embedding function")
#         collection = chroma_client.get_collection(name=collection_name)
#         using_embeddings = False
    
#     print("Querying collection with:", question)
#     print("Total documents in collection:", collection.count())
#     print(f"Using embeddings: {using_embeddings}")
    
#     # Query the collection - use 3 results for better context
#     results = collection.query(
#         query_texts=[question],
#         n_results=3
#     )
    
#     # Format the retrieved contexts
#     contexts = []
#     for i, doc in enumerate(results['documents'][0]):
#         contexts.append(f"Context {i+1}: {doc}")
    
#     context_text = "\n\n".join(contexts)
    
#     client = OpenAI()
    
#     system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
#         but you only answer using knowledge I provide. You don't make things up. If you don't
#         know the answer just apologise for your lack of knowledge and say you don't know.
#         The data: {context_text}"""
    
#     response = client.chat.completions.create(
#         model="gpt-4o",
#         messages=[{"role": "system", "content": system_prompt},
#                   {"role": "user", "content": question}]
#     )
    
#     return response.choices[0].message.content


# def rag2(question, collection_name="hospital_db"):
#     try:
#         # First try to get the collection with the embedding function
#         collection = chroma_client.get_collection(name=collection_name, embedding_function=openai_ef)
#         using_embeddings = True
#     except ValueError as e:
#         # If there's a mismatch, fall back to the default embedding function
#         print(f"Note: {e}")
#         print("Falling back to the default embedding function")
#         collection = chroma_client.get_collection(name=collection_name)
#         using_embeddings = False
    
#     print("Querying collection with:", question)
#     print("Total documents in collection:", collection.count())
#     print(f"Using embeddings: {using_embeddings}")
    
#     # Query the collection - use 3 results for better context
#     results = collection.query(
#         query_texts=[question],
#         n_results=3
#     )
    
#     # Format the retrieved contexts
#     contexts = []
#     for i, doc in enumerate(results['documents'][0]):
#         contexts.append(f"Context {i+1}: {doc}")
    
#     context_text = "\n\n".join(contexts)
    
#     system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
#         but you only answer using knowledge I provide. You don't make things up. If you don't
#         know the answer just apologise for your lack of knowledge and say you don't know. You respond
#         with a single answer only and give me only one response, not multiple. You respond only to the question
#         asked, anything said before it is irrelevant.
#         The data: {context_text}"""
    
#     event = {
#         "type": "response.create",
#         "response": {
#             # Setting to "none" indicates the response is out of band,
#             # and will not be added to the default conversation
#             "conversation": "none",
            
#             # Set metadata to help identify responses sent back from the model
#             "metadata": { "topic": "rag" },
            
#             # Set any other available response fields
#             "modalities": [ "text", "audio"],
#             "instructions": system_prompt,
#             "input": []
#         },
#     }
    
#     return event

# if __name__ == "__main__":
#     client = chromadb.PersistentClient(path="./chroma_db")
#     print(client.list_collections())
from openai import OpenAI
from dotenv import load_dotenv
import os
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore

load_dotenv()

# Make sure these environment variables are set in your .env file
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
QDRANT_URL = os.environ.get("QDRANT_URL")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY")
DATA_PATH = "./data/hospital_data.pdf"

# Initialize OpenAI embedding model - same as used in fill_db.py
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def rag(question, collection_name="hospital_db"):
    """
    RAG function using Qdrant as vector store.
    Returns a text response directly.
    """
    # Initialize the Qdrant vector store
    vector_store = QdrantVectorStore.from_existing_collection(
        url=QDRANT_URL, 
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
        embedding=embeddings
    )
    
    print("Querying collection with:", question)
    
    # Search for relevant documents
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    contexts = retriever.invoke(question)
    
    # Format the retrieved contexts
    formatted_contexts = []
    for i, doc in enumerate(contexts):
        formatted_contexts.append(f"Context {i+1}: {doc.page_content}")
    
    context_text = "\n\n".join(formatted_contexts)
    
    client = OpenAI()
    
    system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
        but you only answer using knowledge I provide. You don't make things up. If you don't
        know the answer just apologise for your lack of knowledge and say you don't know.
        The data: {context_text}"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": question}]
    )
    
    return response.choices[0].message.content


def rag2(question, collection_name="hospital_db"):
    """
    RAG function using Qdrant as vector store.
    Returns an event structure for out-of-band response handling.
    """
    # Initialize the Qdrant vector store
    vector_store = QdrantVectorStore.from_existing_collection(
        url=QDRANT_URL, 
        api_key=QDRANT_API_KEY,
        collection_name=collection_name,
        embedding=embeddings
    )
    
    print("Querying collection with:", question)
    
    # Search for relevant documents
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    contexts = retriever.invoke(question)
    
    # Format the retrieved contexts
    formatted_contexts = []
    for i, doc in enumerate(contexts):
        formatted_contexts.append(f"Context {i+1}: {doc.page_content}")
    
    context_text = "\n\n".join(formatted_contexts)
    
    system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
        but you only answer using knowledge I provide. You don't make things up. If you don't
        know the answer just apologise for your lack of knowledge and say you don't know. You respond
        with a single answer only and give me only one response, not multiple. You respond only to the question
        asked, anything said before it is irrelevant.
        The data: {context_text}"""
    
    event = {
        "type": "response.create",
        "response": {
            # Setting to "none" indicates the response is out of band,
            # and will not be added to the default conversation
            "conversation": "none",
            
            # Set metadata to help identify responses sent back from the model
            "metadata": { "topic": "rag" },
            
            # Set any other available response fields
            "modalities": [ "text", "audio"],
            "instructions": system_prompt,
            "input": []
        },
    }
    
    return event


if __name__ == "__main__":
    response = rag("Where is Greenview medical centre located?")
    print(response)