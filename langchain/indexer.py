import hashlib

class Indexer:
    def __init__(self, collection, whoosh_index, chunked_content, batch_size=100):
        self.collection = collection
        self.chunked_content = chunked_content
        self.batch_size = batch_size

        self.whoosh_index = whoosh_index

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
    
    def index_whoosh(self):
        """
        Index the content using Whoosh-Reloaded, separate from ChromaDB indexing.
        """
        ids, texts, metadatas = self.get_ready()
        print(f"Total chunks to index in Whoosh: {len(ids)}")
        
        # Get the writer to add documents to the index
        writer = self.whoosh_index.writer()
        
        # Process in batches
        for i in range(0, len(ids), self.batch_size):
            end_idx = min(i + self.batch_size, len(ids))
            batch_ids = ids[i:end_idx]
            batch_texts = texts[i:end_idx]
            batch_metadatas = metadatas[i:end_idx]
            
            print(f"Indexing Whoosh batch {i//self.batch_size + 1}: chunks {i} to {end_idx-1}")
            
            try:
                for j in range(len(batch_ids)):
                    writer.add_document(
                        id=batch_ids[j],
                        content=batch_texts[j],
                        page_number=batch_metadatas[j]["page_number"],
                        source=batch_metadatas[j]["source"]
                    )
                print(f"Successfully prepared Whoosh batch {i//self.batch_size + 1}")
                
            except Exception as e:
                print(f"Whoosh indexing failed for batch {i//self.batch_size + 1}: {e}")
        
        # Commit all the changes
        writer.commit()
        print("Whoosh indexing complete!")
        return
