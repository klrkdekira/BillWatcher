import pathlib
import sys

import nest_asyncio
from llama_index.core import (
    Settings,
    VectorStoreIndex,
)
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

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

qdrant_client = QdrantClient(url="http://127.0.0.1:6333")
vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name="bills",
    prefer_grpc=True,
)


index = VectorStoreIndex.from_vector_store(
    vector_store,
    embed_model=embedding,
)


if __name__ == "__main__":
    chat_engine = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        # memory=memory,
        llm=llm,
        context_prompt=(
            "Prefix the answer with IANAL (I Am Not A Lawyer).\n"
            "You are a chatbot, able to have normal interactions, especially about Parliament Bill and Malaysian Law and Legislature.\n"
            "Do not show file_path in asnwer.\n"
            "Only answer questions about law, bill, draft bill, legislature, reading, amendment, act, statutory.\n"
            "Do not answer questions unrelated to the bill.\n"
            "Do not include sources from news and wikipedia.\n"
            "Exclude bill that are not related to Malaysia.\n"
            "Only answer questions about law, bill, act in Malaysia.\n"
            "Reference the code and full name to the latest related law, bill, act.\n"
            "Show the full name of the bill as title, for example D.R.01/1990 - Supplementary Supply (1989) Bill 1990 (Passed).\n"
            "Include the url metadata for document cited.\n"
            "Include the latest amendment of the law, bill, act.\n"
            "Cite every related law, bill, act.\n"
            "Include the amendment and year of the law, bill, act.\n"
            "Include history of reading and approval of law, bill, act.\n"
            "Arrange the law, bill, acts in chronological order.\n"
            "Do not show file_path in asnwer.\n"
            "Here are the relevant law, bill, acts for the context:\n"
            "{context_str}"
            "\nInstruction: Use the previous chat history, or the context above, to interact and help the user."
        ),
        verbose=False,
    )

    prompt = sys.argv[1]
    response = chat_engine.stream_chat(prompt)
    for token in response.response_gen:
        print(token, end="")
