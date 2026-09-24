import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size = 2000,
    chunk_overlap  = 200,
    length_function = len,
    is_separator_regex = False,
)


def split_data_from_file(file):
    chunks_with_metadata = [] 
    
    with open(file, encoding='utf-8') as f:
        file_as_object = json.load(f)
    keys = list(file_as_object.keys())
    print(keys)
    for item in keys: 
        print(f'Processing {item} from {file}') 
        
        item_text = file_as_object[item] 
        
        item_text_chunks = text_splitter.split_text(item_text) 
        
        chunk_seq_id = 0
        for chunk in item_text_chunks: 
        
            form_name = file[file.rindex('/') + 1:file.rindex('.')]
            
            chunks_with_metadata.append({
                'text': chunk, 
                'Source': item,
                'chunkSeqId': chunk_seq_id,
                'chunkId': f'{form_name}-{item}-chunk{chunk_seq_id:04d}',
                
          
            })
            chunk_seq_id += 1
        print(f'\tSplit into {chunk_seq_id} chunks')
    return chunks_with_metadata