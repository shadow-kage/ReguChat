from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(text):

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " "]
    )

    return splitter.split_text(text)