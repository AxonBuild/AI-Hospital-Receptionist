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