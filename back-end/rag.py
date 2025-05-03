import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from fill_db import fill_db
import json

DATA_PATH = "./data/hospital_data.pdf"
CHROMA_PATH = "./chroma_db"

def rag(question, chroma_path = CHROMA_PATH, collection_name = "hospital_db"):
    load_dotenv()

    chroma_client = chromadb.PersistentClient(path=chroma_path)

    collection = chroma_client.get_collection(name=collection_name)

    results = collection.query(query_texts=[question], n_results = 1)
    print("Querying collection with:", question)
    print("Total documents in collection:", collection.count())
    results = collection.query(query_texts=[question], n_results=1)
    print("Query results:", results)

    client = OpenAI()

    system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
        but you only answer using knowledge I provide. You don't make things up. If you don't
        know the answer just apologise for your lack of knowledge and say you don't know.
        The data: {str(results['documents'])}"""

    response = client.chat.completions.create(
        model = "gpt-4o",
        messages = [{"role": "system", "content": system_prompt},
                    {"role": "user", "content": question}]
    )

    return response.choices[0].message.content

def rag2(ws, question, chroma_path = CHROMA_PATH, collection_name = "hospital_db"):
    load_dotenv()

    chroma_client = chromadb.PersistentClient(path=chroma_path)

    collection = chroma_client.get_collection(name=collection_name)
    
    print("Querying collection with:", question)
    print("Total documents in collection:", collection.count())
    results = collection.query(query_texts=[question], n_results=1)
    print("Query results:", results)

    system_prompt = f"""You are a helpful assistant. You answer questions about greenview hospital, 
        but you only answer using knowledge I provide. You don't make things up. If you don't
        know the answer just apologise for your lack of knowledge and say you don't know. You respond
        with a single answer only and give me only one response, not multiple.
        The data: {str(results['documents'])}"""

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
        },
    }
    ws.send(json.dumps(event))
        
if __name__ == "__main__":
    client = chromadb.PersistentClient(path="./chroma_db")
    print(client.list_collections())

    print(rag("Where is Greenview Hospital located?"))