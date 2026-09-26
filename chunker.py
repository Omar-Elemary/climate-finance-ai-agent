import os
import json
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter

def run_chunker():
    os.makedirs("data/chunks", exist_ok=True)
    raw_dir = "data/raw"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    
    all_chunks = []
    print("Starting the chunking process...")
    
    for filename in os.listdir(raw_dir):
        if filename.endswith(".md"):
            filepath = os.path.join(raw_dir, filename)
            
            with open(filepath, "r", encoding="utf-8") as file:
                content = file.read()
            
            # Extract the source URL from the first line (<!-- Source: https://... -->)
            source_url = "Unknown Source"
            first_line = content.split('\n', 1)[0]
            url_match = re.search(r'<!-- Source:\s*(.*?)s*-->', first_line)
            if url_match:
                source_url = url_match.group(1).strip()
            
            # Split the text (ignoring the HTML comment at the top)
            chunks = splitter.split_text(content)
            
            for i, chunk_text in enumerate(chunks):
                # Skip chunks that only contain the HTML comment
                if chunk_text.strip().startswith("<!-- Source:"):
                    continue
                    
                all_chunks.append({
                    "chunk_id": f"{filename}_chunk_{i}",
                    "parent_doc_id": filename.replace(".md", ""),
                    "source_url": source_url,
                    "text": chunk_text
                })
                
    output_file = "data/chunks/master_chunks.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=4)
        
    print(f"Success! Sliced your documents into {len(all_chunks)} total chunks.")
    print(f"Saved database payload to {output_file}")

if __name__ == "__main__":
    run_chunker()