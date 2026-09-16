import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()


MODEL_NAME = "gemini-3.1-flash-lite"
MAX_TOKENS = 8000

PROXY_URL = os.getenv(
    "LLM_PROXY_URL",
    "http://127.0.0.1:12334"
)


def load_model():
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        client_args={
            "proxy": PROXY_URL
        }
    )

    return llm