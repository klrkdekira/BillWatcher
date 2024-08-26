import sys

# monkey patching sqlite3 to use pysqlite3
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import pathlib

import chromadb
import nest_asyncio
from llama_index.core import (
    Settings,
    VectorStoreIndex,
)
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.chroma import ChromaVectorStore

nest_asyncio.apply()

if len(sys.argv) != 2:
    print("Usage: python prompt.py <prompt>")
    sys.exit(1)


VECTOR_DIR = pathlib.Path("vector_data")
VECTOR_DIR.mkdir(exist_ok=True)

memory = ChatMemoryBuffer.from_defaults(token_limit=3900)

llm = Ollama(
    model="llama3.1",
    base_url="http://100.64.0.37:11434",
    request_timeout=120,
)

embedding = OllamaEmbedding(
    model_name="mxbai-embed-large",
    base_url="http://100.64.0.37:11434",
    ollama_additional_kwargs={"microstat": 0},
)

Settings.llm = llm
Settings.embed_model = embedding

chroma_client = chromadb.PersistentClient(VECTOR_DIR.as_posix())
chroma_collection = chroma_client.get_collection("reports")
vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

index = VectorStoreIndex.from_vector_store(
    vector_store,
    embed_model=embedding,
)

# vector_tool = QueryEngineTool(
#     index.as_query_engine(top_k=10),
#     metadata=ToolMetadata(
#         name="vector_search",
#         description="Useful for searching for specific facts.",
#     ),
# )

# summary_tool = QueryEngineTool(
#     index.as_query_engine(response_mode="tree_summarize", top_k=10),
#     metadata=ToolMetadata(
#         name="summary",
#         description="Useful for summarizing an entire document.",
#     ),
# )

# query_engine = RouterQueryEngine.from_defaults(
#     [vector_tool, summary_tool],
#     select_multi=False,
#     verbose=False,
#     llm=llm,
# )


if __name__ == "__main__":
    chat_engine = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        memory=memory,
        llm=llm,
        context_prompt=(
            "You are a chatbot, able to have normal interactions, especially about Parliament Bill and Malaysian Law\n"
            "Prefix the answer with IANAL (I Am Not A Lawyer)\n"
            "Always starts with exact name of the and code of the bill in citations, avoid showing file_path.\n"
            "Provide provide history of reading and approval of bills.\n"
            "Include the latest amendment as much as possible, current year is 2024.\n"
            "Here are the relevant documents for the context:\n"
            "{context_str}"
            "\nInstruction: Use the previous chat history, or the context above, to interact and help the user."
        ),
        verbose=False,
    )

    prompt = sys.argv[1]
    response = chat_engine.stream_chat(prompt)
    for token in response.response_gen:
        print(token, end="")
