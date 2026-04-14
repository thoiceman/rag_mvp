from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter


def get_text_splitters(chunk_size: int = 500, chunk_overlap: int = 80):
    """
    返回 Markdown 标题切片器和递归字符切片器。
    先使用 Markdown 切片器根据标题拆分段落（保留语义边界），
    然后再使用递归字符切片器处理过长的大段落。
    """
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    rec_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""],
    )
    
    return md_splitter, rec_splitter