import os

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()
# """
# اينجا Environment Variables هارو لود ميكنيم
# """


# """
# هدف اين فايل اينكه در پروژمون بيايم 
#  Centralized Configuration ‌انجام بديم
# """

MODEL_NAME = "gemini-3.1-flash-lite"
MAX_TOKENS = 8000

PROXY_URL = os.getenv(
    "LLM_PROXY_URL",
    "http://127.0.0.1:12334"
)

# os.getenv() می‌تواند دو argument بگیرد:
#os.getenv(KEY, DEFAULT_VALUE)
#يعني اگر مقدار key در فايل .env نبود پس بيا و 
# fallback بزن مقدار پيش فرض رو بگير



# اين تابع مسول ساخت llm client‌است 
#اينجا داريم از google provider براي 
# inference گرفتن از مدل استفاده ميكنيم
#حالا اصلا چرا مدل رو return ‌ميكنيم؟
# چون نميخواهيم هر ماژول براي خودش يك مدل جديد بسازه


def load_model():
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        client_args={
            "proxy": PROXY_URL
        }
    )

    return llm