from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb

def fill_db(chroma_path, collection_name, file_path):
    #initialisation
    CHROMA_PATH = chroma_path
    chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = chroma_client.get_or_create_collection(name=collection_name)
    #load document
    loader = PyPDFLoader(file_path=file_path)
    raw_documents = loader.load()
    #split document
    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 300, chunk_overlap = 100, length_function = len, is_separator_regex = False)
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
        
    collection.upsert(documents=documents, metadatas=metadata, ids=ids)
