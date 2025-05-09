import chromadb
from chromadb.utils import embedding_functions

import os
from whoosh.index import create_in, open_dir
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh import scoring
from whoosh.fields import Schema, TEXT, ID, NUMERIC

class DB:
    def __init__(self, db_name, whoosh_index_dir, embedding_model="all-MiniLM-L6-v2"):
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
                embedding_function=self.embedding_function,
                metadata={
                    "hnsw:space": "cosine"
                }
            )
            print("Connected to Chroma!")
        
        except Exception as e:
            print(f"Error connecting to Chroma : {e}")

        self.whoosh_index_dir = os.path.join("whoosh", whoosh_index_dir)
        self.whoosh_index = None

        # Create the Whoosh schema
        schema = Schema(
            id=ID(stored=True, unique=True),
            content=TEXT(stored=True),
            page_number=NUMERIC(stored=True),
            source=ID(stored=True)
        )
        
        # Create the directory for the Whoosh index if it doesn't exist
        if not os.path.exists(self.whoosh_index_dir):
            os.makedirs(self.whoosh_index_dir)
            # Create a new index
            self.whoosh_index = create_in(self.whoosh_index_dir, schema)
            print(f"Created Whoosh index at {self.whoosh_index_dir}")
        else:
            # Open the existing index
            try:
                self.whoosh_index = open_dir(self.whoosh_index_dir)
                print(f"Opened Whoosh index at {self.whoosh_index_dir}")
            except:
                # If there's an issue opening the index, create a new one
                self.whoosh_index = create_in(self.whoosh_index_dir, schema)
    
    def get_collection(self):
        return self.collection
    
    def get_whoosh_index(self):
        return self.whoosh_index
    
    def query(self, queries, top_k=10):
        
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
        
    
    def query_whoosh(self, query_text, fields=None, limit=10):
        """
        Query the Whoosh index with the given query text.
        
        Args:
            query_text (str): The text to search for
            fields (list): List of fields to search in (default: ["content"])
            limit (int): Maximum number of results to return
            
        Returns:
            list: A list of dictionaries containing the search results
        """
        if self.whoosh_index is None:
            # Try to open the index if it exists
            if os.path.exists(self.whoosh_index_dir):
                self.whoosh_index = open_dir(self.whoosh_index_dir)
            else:
                raise ValueError("Whoosh index has not been created yet. Call index_whoosh() first.")
        
        # Set default fields if not provided
        if fields is None:
            fields = ["content"]
        
        # Create a searcher to query the index
        with self.whoosh_index.searcher(weighting=scoring.BM25F()) as searcher:
            if len(fields) > 1:
                parser = MultifieldParser(fields, self.whoosh_index.schema)
            else:
                parser = QueryParser(fields[0], self.whoosh_index.schema)
            
            # Parse the query string
            query = parser.parse(query_text)
            
            # Search the index
            results = searcher.search(query, limit=limit)
            
            # Just return the document contents in an array
            documents = [hit["content"] for hit in results]
            
            return documents
