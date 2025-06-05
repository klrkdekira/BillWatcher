import json
import multiprocessing
import pathlib
from contextlib import asynccontextmanager
from functools import cache

import anyio
import httpx
import nest_asyncio
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
)
from llama_index.core.extractors import (
    QuestionsAnsweredExtractor,
    SummaryExtractor,
)
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode
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
    model="gemma3:12b",
    base_url="http://10.3.0.173:11434",
    request_timeout=120,
    temperature=0,
    context_window=32768,
)

llm_local = Ollama(
    model="gemma3:12b",
    base_url="http://10.3.0.173:11434",
    request_timeout=120,
    temperature=0,
    context_window=32768,
)

embedding = OllamaEmbedding(
    model_name="snowflake-arctic-embed2:latest",
    base_url="http://10.3.0.173:11434",
    ollama_additional_kwargs={"microstat": 0},
)

# rerank = SentenceTransformerRerank(
#     model="cross-encoder/ms-marco-MiniLM-L-2-v2", top_n=3
# )

Settings.llm = llm_local
Settings.embed_model = embedding


@cache
def get_metadata(file_path: str) -> dict:
    try:
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
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading metadata for {file_path}: {e}")
        return {}


@asynccontextmanager
async def get_qdrant_clients():
    qdrant_client = QdrantClient(url="http://127.0.0.1:6333")
    qdrant_aclient = AsyncQdrantClient(url="http://127.0.0.1:6333")
    try:
        yield qdrant_client, qdrant_aclient
    finally:
        await qdrant_aclient.close()
        qdrant_client.close()


async def main():
    try:
        async with get_qdrant_clients() as (qdrant_client, qdrant_aclient):
            vector_store = QdrantVectorStore(
                aclient=qdrant_aclient,
                client=qdrant_client,
                collection_name="bills",
                prefer_grpc=True,
            )

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
                    SentenceSplitter(chunk_size=2048, chunk_overlap=128),
                    SummaryExtractor(
                        llm=llm, metadata_mode=MetadataMode.EMBED, num_workers=num_cpu
                    ),
                    QuestionsAnsweredExtractor(
                        llm=llm, questions=3, embedding_only=True
                    ),
                    embedding,
                ],
                vector_store=vector_store,
            )

            pipeline_storage_path = pathlib.Path("./pipeline_storage")

            if pipeline_storage_path.exists():
                try:
                    pipeline.load("./pipeline_storage")
                    print("Loaded existing pipeline storage")
                except Exception as e:
                    print(f"Error loading pipeline storage: {e}")
                    print("Proceeding with new pipeline")

            nodes = await pipeline.arun(
                documents=documents, num_workers=num_cpu, show_progress=True
            )

            try:
                pipeline.persist("./pipeline_storage")
            except Exception as e:
                print(f"Error persisting pipeline: {e}")

            print(f"Processed {len(nodes)} nodes")

    except Exception as e:
        print(f"An error occurred: {e}")
        raise


if __name__ == "__main__":
    anyio.run(main, backend="asyncio")
