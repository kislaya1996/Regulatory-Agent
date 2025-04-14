import hashlib

class Indexer:
    def __init__(self, collection, chunked_content, batch_size=100):
        self.collection = collection
        self.chunked_content = chunked_content
        self.batch_size = batch_size 

    def get_ready(self):
        
        check = set()
        ids = []
        texts = []
        metadatas = []

        for chunk in self.chunked_content:
            temp = hashlib.blake2b(chunk["content"].encode()).hexdigest()

            if temp not in check:
                check.add(temp)

                # Now add the chunk to the lists
                ids.append(temp)
                texts.append(chunk["content"])
                metadatas.append({"page_number": chunk["page_number"], "source": chunk["source"]})

        return ids, texts, metadatas

    def index(self):
        
        ids, texts, metadatas = self.get_ready()
        print(f"Total chunks to index: {len(ids)}")
        
        # Process in batches to avoid overwhelming the database
        for i in range(0, len(ids), self.batch_size):
            end_idx = min(i + self.batch_size, len(ids))
            batch_ids = ids[i:end_idx]
            batch_texts = texts[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            
            print(f"Indexing batch {i//self.batch_size + 1}: chunks {i} to {end_idx-1}")
            
            try:
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                print(f"Successfully indexed batch {i//self.batch_size + 1}")
                
            except Exception as e:
                print(f"Indexing failed for batch {i//self.batch_size + 1}: {e}")
                
        print("Indexing complete!")
        return
