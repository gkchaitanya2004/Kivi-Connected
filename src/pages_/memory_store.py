import chromadb 

def create_memory_collection(email):
    username = email.replace("@", "_").replace(".", "_")
    collection_name = f"{username}_memory"
    client = chromadb.PersistentClient(path="chroma_db")  
    collection = client.get_or_create_collection(name=collection_name) 
    return collection


def add_memory_embedding(email, ids, docs, metadatas):
    db = create_memory_collection(email)
    db.add(
        ids=[str(ids)],
        documents=[docs],
        metadatas=[metadatas]
    )


def retrive_memory_embeddings(email, query, n_results=5):
    db = create_memory_collection(email)

    if not db.count():
        return [] 

    else:

        results = db.query(
            query_texts=[query],
            n_results=n_results
        )
        return results