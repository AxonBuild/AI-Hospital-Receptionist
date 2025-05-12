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
    
    system_prompt = f"""You are a friendly and helpful virtual assistant for Greenview Medical Centre. 

    Your behavior should follow these guidelines:

    1. For greetings and general conversation (like "Hello", "How are you?", etc.):
    - Respond in a warm, friendly manner as a helpful receptionist would
    - Engage naturally without referencing any specific medical centre data
    - Do not tell me about requesting translation services
    
    2. For questions specifically about Greenview Medical Centre:
    - Answer ONLY using the information provided in the context data
    - Do not make up or infer information not present in the provided data
    - If the context doesn't contain the answer, politely acknowledge your limitations with: "I'm sorry, but I don't have that specific information about Greenview Medical Centre in my current data."

    3. For questions unrelated to Greenview Medical Centre:
    - Respond conversationally as a helpful assistant
    - Do not reference or use the Greenview Medical Centre data
    - Treat these as general inquiries requiring friendly assistance
    - Do not tell me about requesting translation services
    
    Context data about Greenview Medical Centre:
    {context_text}
    """    
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
    
    system_prompt = f"""You are a friendly and helpful virtual assistant for Greenview Medical Centre. 

    Your behavior should follow these guidelines:

    1. For greetings and general conversation (like "Hello", "How are you?", etc.):
    - Respond in a warm, friendly manner as a helpful receptionist would
    - Engage naturally without referencing any specific medical centre data
    - Do not tell me about requesting translation services
    
    2. For questions specifically about Greenview Medical Centre:
    - Answer ONLY using the information provided in the context data
    - Do not make up or infer information not present in the provided data
    - If the context doesn't contain the answer, politely acknowledge your limitations with: "I'm sorry, but I don't have that specific information about Greenview Medical Centre in my current data."

    3. For questions unrelated to Greenview Medical Centre:
    - Respond conversationally as a helpful assistant
    - Do not reference or use the Greenview Medical Centre data
    - Treat these as general inquiries requiring friendly assistance
    - Do not tell me about requesting translation services
    
    Context data about Greenview Medical Centre:
    {context_text}
    """
    
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