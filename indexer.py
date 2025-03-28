import hashlib

class Indexer:
    def __init__(self, collection, chunked_content):
        self.collection = collection
        self.chunked_content = chunked_content

    def get_ready(self):
        ids = []
        texts = []
        metadatas = []

        for chunk in self.chunked_content:
            ids.append(hashlib.blake2b(chunk["content"].encode()).hexdigest())
            texts.append(chunk["content"])
            metadatas.append({"page_number" : chunk["page_number"], "source" : chunk["source"]})

        return ids, texts, metadatas

    def index(self):
        ids, texts, metadatas = self.get_ready()

        print(ids,'\n',texts,'\n', metadatas, '\n')
        
        try:
            self.collection.add(
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
        
        except Exception as e:
            print(f"Indexing failed: {e}")


