import chromadb
from chromadb.utils import embedding_functions

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
            self.collection = client.get_or_create_collection(name=self.db_name)
            print("Connected to Chroma!")
        
        except Exception as e:
            print(f"Error connecting to Chroma : {e}")

    def get_collection(self):
        return self.collection             
    
    def query(self, queries, top_k=10):
        
        try:
            retreival = self.collection.query(
                query_texts=queries,
                n_results=top_k
            )

            return retreival

        except Exception as e:
            print(f"Error in retreival from Chroma : {e}")
            return None


        
