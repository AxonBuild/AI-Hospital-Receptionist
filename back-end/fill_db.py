# from langchain_community.document_loaders import PyPDFLoader
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# import chromadb

# def fill_db(chroma_path = "./chroma_db", collection_name = "hospital_db", file_path = "./data/hospital_data.pdf"):
#     #initialisation
#     CHROMA_PATH = chroma_path
#     chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
#     collection = chroma_client.get_or_create_collection(name=collection_name)
#     #load document
#     loader = PyPDFLoader(file_path=file_path)
#     raw_documents = loader.load()
#     #split document
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size = 300, chunk_overlap = 100, length_function = len, is_separator_regex = False)
#     chunks = text_splitter.split_documents(raw_documents)
#     documents = []
#     metadata = []
#     ids = []

#     i = 0

#     for chunk in chunks:
#         documents.append(chunk.page_content)
#         ids.append(str(i))
#         i += 1
#         metadata.append(chunk.metadata)
        
#     collection.upsert(documents=documents, metadatas=metadata, ids=ids)

# if __name__ == "__main__":
#     fill_db()
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions
import os
from dotenv import load_dotenv

def fill_db(chroma_path = "./chroma_db", collection_name = "hospital_db", file_path = "./data/hospital_data.pdf"):
    # Load environment variables (for OpenAI API key)
    load_dotenv()
    
    # Initialize ChromaDB
    CHROMA_PATH = chroma_path
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Set up embedding function using OpenAI
    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ.get("OPENAI_API_KEY"),
        model_name="text-embedding-3-small"
    )
    
    # If collection exists, delete it first to ensure consistent embedding settings
    try:
        existing_collections = chroma_client.list_collections()
        collection_names = [col.name for col in existing_collections]
        if collection_name in collection_names:
            chroma_client.delete_collection(name=collection_name)
            print(f"Deleted existing collection '{collection_name}' to create a fresh one with embeddings")
    except Exception as e:
        print(f"Note: {e}")
    
    # Create collection with the embedding function
    collection = chroma_client.create_collection(
        name=collection_name,
        embedding_function=openai_ef
    )
    
    # Load document
    loader = PyPDFLoader(file_path=file_path)
    raw_documents = loader.load()
    
    # Split document
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False
    )
    chunks = text_splitter.split_documents(raw_documents)
    
    documents = []
    metadata = []
    ids = []
    
    i = 0
    
    for chunk in chunks:
        documents.append(chunk.page_content)
        ids.append(str(i))
        i += 1
        metadata.append(chunk.metadata)
    
    # Add documents to collection (embeddings are computed automatically)
    collection.upsert(documents=documents, metadatas=metadata, ids=ids)
    print(f"Added {len(documents)} documents to collection '{collection_name}' with OpenAI embeddings")

if __name__ == "__main__":
    fill_db()