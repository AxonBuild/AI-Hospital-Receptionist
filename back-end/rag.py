import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from fill_db import fill_db

DATA_PATH = "./data/hospital_data.pdf"
CHROMA_PATH = "./chroma_db"

def rag(question, chroma_path, collection_name):
    load_dotenv()

    chroma_client = chromadb.PersistentClient(path=chroma_path)

    collection = chroma_client.get_collection(name=collection_name)

    query = input(question + " : ")

    results = collection.query(query_texts=[query], n_results = 1)

    client = OpenAI()

    system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
        but you only answer using knowledge I provide. You don't make things up. If you don't
        know the answer just apologise for your lack of knowledge and say you don't know.
        The data: {str(results['documents'])}"""

    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}]
    )

    print(response.choices[0].message.content)