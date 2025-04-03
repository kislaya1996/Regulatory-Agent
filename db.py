import chromadb
from chromadb.utils import embedding_functions
import hashlib

class DB:
    def __init__(self, db_name, embedding_model="all-MiniLM-L6-v2"):
        self.db_name = db_name
        self.collection = None
        self.embedding_model = embedding_model

        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=embedding_model
        )

        try:
            client = chromadb.PersistentClient()
            self.collection = client.get_or_create_collection(
                name=self.db_name, 
                embedding_function=self.embedding_function
            )
            print("Connected to Chroma!")
        
        except Exception as e:
            print(f"Error connecting to Chroma : {e}")

    def get_ready(self, chunked_content):
        ids = []
        texts = []
        metadatas = []

        for chunk in chunked_content:
            ids.append(hashlib.blake2b(chunk["content"].encode()).hexdigest())
            texts.append(chunk["content"])
            metadatas.append({"page_number" : chunk["page_number"], "source" : chunk["source"]})

        return ids, texts, metadatas

    def index(self, chunked_content, batch_size=100):
        ids, texts, metadatas = self.get_ready(chunked_content)
        print(f"Total chunks to index: {len(ids)}")

        # Process in batches to avoid overwhelming the database
        for i in range(0, len(ids), batch_size):
            end_idx = min(i + batch_size, len(ids))
            batch_ids = ids[i:end_idx]
            batch_texts = texts[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            
            print(f"Indexing batch {i//batch_size + 1}: chunks {i} to {end_idx-1}")
            
            try:
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                print(f"Successfully indexed batch {i//batch_size + 1}")
                
            except Exception as e:
                print(f"Indexing failed for batch {i//batch_size + 1}: {e}")
                
        print("Indexing complete!")
        return    
    
    def query(self, queries, top_k=5):
        
        try:
            count = self.collection.count()
            if count == 0:
                print(f"Warning: Collection '{self.db_name}' is empty. No documents to search.")
                return None
            
            retreival = self.collection.query(
                query_texts = queries,
                n_results = min(top_k, count)
            )

            return retreival["documents"][0]

        except Exception as e:
            print(f"Error in retreival from Chroma : {e}")
            return None


        
