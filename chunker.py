from langchain.text_splitter import RecursiveCharacterTextSplitter

class Chunker:
    def __init__(self, document, chunk_size=300, overlap=30):
        self.document = document
        self.chunked_content = []
        self.chunk_size = chunk_size
        self.overlap = overlap

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.overlap,
            separators=["\n\n", "\n", ".", " ", ""],
            keep_separator=False
        )

    def chunk(self):
        try:
            for page in self.document:
                page_num = page["page_number"]
                page_content = page["content"]
                page_source = page["source"]

                if len(page_content) > self.chunk_size * 1.5:
                    page_chunks = self.text_splitter.split_text(page_content)

                    for chunk in page_chunks:
                        self.chunked_content.append({
                            "page_number": page_num,
                            "content": chunk,
                            "source": page_source
                        })
                        
                else:
                    self.chunked_content.append(page)
            
            return self.chunked_content
        
        except Exception as e:
            
            print(f"Error chunking text: {e}")
            return []        

