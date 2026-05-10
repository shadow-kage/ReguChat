from langchain_text_splitters import RecursiveCharacterTextSplitter

# Module-level to avoid reconstructing on every call.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=2000,
    chunk_overlap=200,
    separators=["\n\n", "\n", ".", " "],
)


def chunk_text(text: str) -> list[str]:
    return _splitter.split_text(text)
