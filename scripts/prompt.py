import pathlib
import re
import sys
from typing import List, Tuple

import nest_asyncio
from llama_index.core import (
    Settings,
    VectorStoreIndex,
)
from llama_index.core.chat_engine import CondensePlusContextChatEngine
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core.postprocessor import (
    LLMRerank,
    LongContextReorder,
)
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


def custom_parse_choice_select_answer_fn(
    answer: str, num_choices: int, raise_error: bool = False
) -> Tuple[List[int], List[float]]:
    """Default parse choice select answer function."""
    answer_lines = answer.split("\n")
    answer_nums = []
    answer_relevances = []
    for answer_line in answer_lines:
        line_tokens = answer_line.split(",")
        if len(line_tokens) != 2:
            if not raise_error:
                continue
            else:
                raise ValueError(
                    f"Invalid answer line: {answer_line}. "
                    "Answer line must be of the form: "
                    "answer_num: <int>, answer_relevance: <float>"
                )
        answers = line_tokens[0].split(":")
        if len(answers) <= 1:
            continue

        answer_num = int(answers[1].strip())
        if answer_num > num_choices:
            continue
        answer_nums.append(answer_num)
        # extract just the first digits after the colon.
        _answer_relevance = re.findall(r"\d+", line_tokens[1].split(":")[1].strip())[0]
        answer_relevances.append(float(_answer_relevance))
    return answer_nums, answer_relevances


rerank = LLMRerank(
    choice_batch_size=5,
    top_n=3,
    parse_choice_select_answer_fn=custom_parse_choice_select_answer_fn,
)

reorder = LongContextReorder()

postprocessors = [reorder, rerank]


if __name__ == "__main__":
    chat_engine = CondensePlusContextChatEngine.from_defaults(
        index.as_retriever(),
        # memory=memory,
        similarity_top_k=10,
        llm=llm,
        node_postprocessors=postprocessors,
        context_prompt=(
            "Prefix every answer with 'IANAL (I Am Not A Lawyer).'\n\n"
            "You are a chatbot specializing in Malaysian law, bills, and the legislative process.\n\n"
            "Strict Guidelines:\n"
            "1. Only respond to questions using information retrieved from the vector database related to Malaysian law, bills, draft bills, legislature, readings, amendments, acts, or statutory matters.\n"
            "2. Do not create or invent any information. If relevant information is not found in the provided context or vector database, respond with 'The requested information is not available.'\n"
            "3. Do not mention or display file paths in your answers.\n"
            "4. When referring to positions such as ministers, mention only the position without using specific names, and only if available from the vector database.\n"
            "5. Avoid answering questions unrelated to Malaysian law or the legislative process.\n"
            "6. Exclude bills and laws that do not pertain to Malaysia.\n"
            "7. Do not use or reference news articles, Wikipedia, or other informal sources. Only cite documents directly retrieved from the vector database.\n\n"
            "Response Structure:\n"
            "1. Title the relevant document or law with its full name, e.g., 'D.R.01/1990 - Supplementary Supply (1989) Bill 1990 (Passed),' only if provided in the vector database.\n"
            "2. Cite the latest version of each law, bill, or act, including amendments and the year of the amendment, only if retrieved from the vector database.\n"
            "3. Provide a brief history of the readings and approval of the law, bill, or act, only if this information is available from the vector database.\n"
            "4. Present all legal documents and references in chronological order, based on the retrieved data.\n\n"
            "If any document or law is referenced, only cite its metadata (URL) if provided by the vector database. Do not generate new URLs or invent references.\n\n"
            "Context:\n"
            "- Refer to the relevant law, bill, or act strictly based on the information provided in the vector database: {context_str}.\n"
            "- Use previous chat history or context to assist the user, but never invent or assume data not provided by the vector database."
        ),
        verbose=False,
    )

    prompt = sys.argv[1]
    response = chat_engine.stream_chat(prompt)
    if response is None:
        print("No response.")
        sys.exit(0)

    for token in response.response_gen:
        print(token, end="")
