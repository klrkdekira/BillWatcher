import json
import multiprocessing
import pathlib
from functools import cache

import httpx
import nest_asyncio
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.core.extractors import SummaryExtractor, TitleExtractor
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor import SentenceTransformerRerank
from llama_index.core.schema import MetadataMode
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient

from billwatcher.config import traverse_bill

nest_asyncio.apply()

MARKDOWN_FILE = "bill.md"
PDF_FILE = "bill.pdf"

# VECTOR_DIR = pathlib.Path("vector_data")
# VECTOR_DIR.mkdir(exist_ok=True)

llm = Ollama(
    model="llama3.1:latest",
    base_url="http://127.0.0.1:11434",
    request_timeout=120,
    temperature=0.1,
)

embedding = OllamaEmbedding(
    model_name="mxbai-embed-large:latest",
    base_url="http://127.0.0.1:11434",
    ollama_additional_kwargs={"microstat": 0},
)

rerank = SentenceTransformerRerank(
    model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3
)

Settings.llm = llm
Settings.embed_model = embedding


@cache
def get_metadata(file_path):
    path = pathlib.Path(file_path).parent / "metadata.json"

    data = json.loads(path.read_text())

    link = str(httpx.URL(f"https://www.parlimen.gov.my{data['document']}"))
    return {
        "year": data["year"],
        "bill": data["bill"],
        "title": data["bill"],
        "filename": data["bill"],
        "category": "parliament",
        "sitename": "https://www.parlimen.gov.my",
        "url": link,
        "file_path": link,
    }


if __name__ == "__main__":
    qdrant_client = QdrantClient(url="http://127.0.0.1:6333")
    qdrant_aclient = AsyncQdrantClient(url="http://127.0.0.1:6333")
    vector_store = QdrantVectorStore(
        # aclient=qdrant_aclient,
        client=qdrant_client,
        collection_name="bills",
        prefer_grpc=True,
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    files = []
    for bill in traverse_bill():
        markdown_path = bill / MARKDOWN_FILE
        if markdown_path.exists() and markdown_path.stat().st_size > 0:
            files.append(markdown_path)

        # pdf_file = bill / PDF_FILE
        # if pdf_file.exists() and pdf_file.stat().st_size > 0:
        #     files.append(pdf_file)

    num_cpu = multiprocessing.cpu_count()
    documents = SimpleDirectoryReader(
        input_files=files, file_metadata=get_metadata
    ).load_data(num_workers=num_cpu)

    pipeline = IngestionPipeline(
        transformations=[
            SentenceSplitter(chunk_size=1024, chunk_overlap=20),
            TitleExtractor(llm=llm, metadata_mode=MetadataMode.EMBED, num_workers=8),
            SummaryExtractor(llm=llm, metadata_mode=MetadataMode.EMBED, num_workers=8),
            embedding,
        ],
        docstore=SimpleDocumentStore(),
        vector_store=vector_store,
    )

    pipeline.persist("./pipeline_storage")

    nodes = pipeline.run(
        documents,
    )

    # VectorStoreIndex.from_documents(
    #     documents,
    #     storage_context=storage_context,
    #     show_progress=True,
    #     embed_model=embedding,
    #     use_async=True,
    # )
