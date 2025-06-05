import re
from typing import List, Tuple

import nest_asyncio
import streamlit as st
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.postprocessor import (
    LLMRerank,
    LongContextReorder,
    SimilarityPostprocessor,
)
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Constants
OLLAMA_BASE_URL = "http://10.3.0.173:11434"
QDRANT_URL = "http://qdrant:6333"
COLLECTION_NAME = "bills"
DEFAULT_RESPONSE = "IANAL Bot ready to assist with Malaysian legal information. Please note that I cannot provide legal advice."

# Initialize async support
nest_asyncio.apply()

# LLM Configuration
llm = Ollama(
    model="gemma3:12b",
    base_url=OLLAMA_BASE_URL,
    request_timeout=120,
    temperature=0.4,
    top_p=0.9,
    context_window=16000,
)

embedding = OllamaEmbedding(
    model_name="snowflake-arctic-embed2:latest",
    base_url=OLLAMA_BASE_URL,
    ollama_additional_kwargs={"microstat": 0},
)

# Streamlit Configuration
st.set_page_config(
    page_title="IANAL Bot",
    page_icon="🦙",
    layout="centered",
    initial_sidebar_state="auto",
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": DEFAULT_RESPONSE}]


@st.cache_resource(show_spinner=True, ttl=3600)
def load_data() -> VectorStoreIndex:
    """
    Load and initialize the vector store index.
    Returns:
        VectorStoreIndex: Initialized vector store index
    """
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL)
        vector_store = QdrantVectorStore(
            client=qdrant_client,
            collection_name=COLLECTION_NAME,
            prefer_grpc=True,
        )

        Settings.llm = llm
        Settings.embed_model = embedding

        return VectorStoreIndex.from_vector_store(
            vector_store,
            embed_model=embedding,
        )
    except Exception as e:
        st.error(f"Failed to load vector store: {str(e)}")
        raise


@st.cache_resource(show_spinner=False)
def load_postprocessors():
    Settings.llm = llm
    Settings.embed_model = embedding

    def custom_parse_choice_select_answer_fn(
        answer: str, num_choices: int, raise_error: bool = False
    ) -> Tuple[List[int], List[float]]:
        """Default parse choice select answer function."""
        if not answer or not isinstance(answer, str):
            return [], []

        if not isinstance(num_choices, int) or num_choices <= 0:
            return [], []

        answer_lines = answer.split("\n")
        answer_nums = []
        answer_relevances = []

        for answer_line in answer_lines:
            try:
                line_tokens = answer_line.split(",")
                if len(line_tokens) != 2:
                    if raise_error:
                        raise ValueError(f"Invalid answer line: {answer_line}")
                    continue

                answers = line_tokens[0].split(":")
                if len(answers) <= 1:
                    continue

                answer_num = int(answers[1].strip())
                if answer_num > num_choices:
                    continue

                answer_nums.append(answer_num)
                _answer_relevance = re.findall(
                    r"\d+", line_tokens[1].split(":")[1].strip()
                )[0]
                answer_relevances.append(float(_answer_relevance))

            except (ValueError, IndexError):
                if raise_error:
                    raise
                continue

        return answer_nums, answer_relevances

    rerank = LLMRerank(
        llm=llm,
        choice_batch_size=5,
        top_n=3,
        parse_choice_select_answer_fn=custom_parse_choice_select_answer_fn,
    )

    reorder = LongContextReorder()

    similarity = SimilarityPostprocessor(similarity_cutoff=0.75)

    return [
        similarity,
        reorder,
        rerank,
    ]


def initialize_chat_engine() -> CondensePlusContextChatEngine:
    """
    Initialize the chat engine with proper configuration.
    Returns:
        CondensePlusContextChatEngine: Configured chat engine
    """
    return CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        similarity_top_k=3,
        memory=ChatMemoryBuffer.from_defaults(token_limit=6000),
        llm=llm,
        return_source_documents=True,
        context_prompt=(
            "IMPORTANT: I am an AI language model, not a lawyer or legal professional. "
            "Every response must begin with: 'IANAL (I Am Not A Lawyer) - This is factual information only, not legal advice.'\n\n"
            "Core Requirements:\n"
            "1. Source Adherence:\n"
            "   - ONLY use information directly present in the retrieved documents\n"
            "   - If a question cannot be answered using the retrieved documents, state: 'I cannot answer this question based on the available documents'\n"
            "   - Do not combine information from different documents unless they are directly related\n"
            "   - Never infer, extrapolate, or create information not present in the sources\n\n"
            "2. Response Structure:\n"
            "   - Reference specific sections and parts from the retrieved documents\n"
            "   - Use direct quotes where possible\n"
            "   - Present only factual content from the documents\n"
            "   - Keep responses concise and focused on the question\n\n"
            "3. Accuracy Controls:\n"
            "   - If information is ambiguous, state: 'The document is unclear on this point'\n"
            "   - If multiple versions exist, specify the version and date\n"
            "   - For partial information, state: 'The documents only provide partial information on this topic'\n"
            "   - Never attempt to fill gaps in information\n\n"
            "4. Prohibited Actions:\n"
            "   - No legal advice or interpretations\n"
            "   - No hypothetical scenarios\n"
            "   - No predictions or speculation\n"
            "   - No combining unrelated pieces of information\n\n"
            "Uncertainty Protocol:\n"
            "- If confidence is low: 'The available documents do not provide a clear answer'\n"
            "- If information is dated: 'This information is from [date], check for updates'\n"
            "- If documents conflict: 'There are conflicting sources on this point'\n\n"
            "Context: {context_str}"
        ),
        verbose=True,
    )


# Initialize components
try:
    index = load_data()
    postprocessors = load_postprocessors()
    if "chat_engine" not in st.session_state:
        st.session_state.chat_engine = initialize_chat_engine()
except Exception as e:
    st.error(f"Failed to initialize components: {str(e)}")
    st.stop()

# Handle user input and generate responses
if prompt := st.chat_input("Ask a question about Malaysian law"):
    st.session_state.messages.append({"role": "user", "content": prompt})

# Display message history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Generate new response if needed
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        try:
            response_stream = st.session_state.chat_engine.stream_chat(prompt)
            st.write_stream(response_stream.response_gen)
            message = {"role": "assistant", "content": response_stream.response}
            st.session_state.messages.append(message)

            if (
                hasattr(response_stream, "source_nodes")
                and response_stream.source_nodes
            ):
                st.write("### References")
                for node in response_stream.source_nodes:
                    if hasattr(node, "metadata") and node.metadata.get("url"):
                        st.write(f"- {node.metadata['url']}")
        except Exception:
            error_message = "IANAL Bot encountered an error. Please try again."
            st.error(error_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )
