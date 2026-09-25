import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()


# """
# اينجا Environment Variables هارو لود ميكنيم
# """


# """
# هدف اين فايل اينكه در پروژمون بيايم 
#  Centralized Configuration ‌انجام بديم
# """


MODEL_NAME = "claude-sonnet-4-6"
MAX_TOKENS = 8000

VYCE_API_KEY = os.getenv("VYCE_API_KEY")
VYCE_BASE_URL = "https://vyceai.com/v1"


def load_model(model_name: str = MODEL_NAME):
    """
    Create the LLM client used by the application.

    Vyce exposes an OpenAI-compatible API, so ChatOpenAI
    can be used with a custom base URL.
    """

    if not VYCE_API_KEY:
        raise ValueError(
            "VYCE_API_KEY was not found in the environment."
        )

    llm = ChatOpenAI(
        model=model_name,
        api_key=VYCE_API_KEY,
        base_url=VYCE_BASE_URL,
        max_tokens=MAX_TOKENS,
        temperature=0,
    )

    return llm

# os.getenv() می‌تواند دو argument بگیرد:
#os.getenv(KEY, DEFAULT_VALUE)
#يعني اگر مقدار key در فايل .env نبود پس بيا و 
# fallback بزن مقدار پيش فرض رو بگير



# اين تابع مسول ساخت llm client‌است 
#اينجا داريم از google provider براي 
# inference گرفتن از مدل استفاده ميكنيم
#حالا اصلا چرا مدل رو return ‌ميكنيم؟
# چون نميخواهيم هر ماژول براي خودش يك مدل جديد بسازه


