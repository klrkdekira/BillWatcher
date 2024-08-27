import sys

# monkey patching sqlite3 to use pysqlite3
__import__("pysqlite3")
sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")

import pathlib

import chromadb
import nest_asyncio
import streamlit as st
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


st.set_page_config(
    page_title="IANAL Bot",
    page_icon="🦙",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)

if "messages" not in st.session_state.keys():  # Initialize the chat messages history
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Ask me but IANAL",
        }
    ]


@st.cache_resource(show_spinner=False)
def load_data():
    chroma_client = chromadb.PersistentClient(VECTOR_DIR.as_posix())
    chroma_collection = chroma_client.get_collection("reports")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    Settings.llm = llm
    Settings.embed_model = embedding
    index = VectorStoreIndex.from_vector_store(
        vector_store,
        embed_model=embedding,
    )

    return index


index = load_data()

if "chat_engine" not in st.session_state.keys():  # Initialize the chat engine
    st.session_state.chat_engine = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        memory=memory,
        llm=llm,
        context_prompt=(
            "You are a chatbot, able to have normal interactions, especially about Parliament Bill and Malaysian Law\n"
            "Prefix the answer with IANAL (I Am Not A Lawyer)\n"
            "Exclude documents and laws that are not related to Malaysia.\n"
            "Always starts with exact code and name of the law, bill and amendment in citations, avoid showing file_path.\n"
            "Provide provide history of reading and approval of bills.\n"
            "Include the latest law, bill and amendment as much as possible, current year is 2024.\n"
            "Here are the relevant documents for the context:\n"
            "{context_str}"
            "\nInstruction: Use the previous chat history, or the context above, to interact and help the user."
        ),
        verbose=False,
    )

if prompt := st.chat_input(
    "Ask a question"
):  # Prompt for user input and save to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

for message in st.session_state.messages:  # Write message history to UI
    with st.chat_message(message["role"]):
        st.write(message["content"])

# If last message is not from assistant, generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response_stream = st.session_state.chat_engine.stream_chat(prompt)
        st.write_stream(response_stream.response_gen)
        message = {"role": "assistant", "content": response_stream.response}
        # Add response to message history
        st.session_state.messages.append(message)
