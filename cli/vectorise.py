import sys

# monkey patching sqlite3 to use pysqlite3
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import pathlib

import chromadb
import nest_asyncio
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

from billwatcher.config import traverse_bill

nest_asyncio.apply()

MARKDOWN_FILE = "bill.md"

VECTOR_DIR = pathlib.Path("vector_data")
VECTOR_DIR.mkdir(exist_ok=True)

llm = Ollama(
    model="llama3.1:latest",
    base_url="http://100.64.0.37:11434",
    request_timeout=120,
)

embedding = OllamaEmbedding(
    model_name="mxbai-embed-large:latest",
    base_url="http://100.64.0.37:11434",
    ollama_additional_kwargs={"microstat": 0},
)

Settings.llm = llm
Settings.embed_model = embedding


if __name__ == "__main__":
    chroma_client = chromadb.PersistentClient(VECTOR_DIR.as_posix())
    chroma_collection = chroma_client.create_collection("reports")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    files = []
    for bill in traverse_bill():
        markdown_path = bill / MARKDOWN_FILE
        if not markdown_path.exists() or markdown_path.stat().st_size == 0:
            continue

        files.append(markdown_path)

    documents = SimpleDirectoryReader(input_files=files).load_data()

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
        embed_model=embedding,
    )
