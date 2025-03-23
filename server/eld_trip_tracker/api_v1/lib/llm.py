import os
from llama_index.llms.gemini import Gemini
from llama_index.core.prompts import PromptTemplate

from dotenv import load_dotenv

load_dotenv()


def get_llm(model_name="models/gemini-1.5-flash"):
    model = Gemini(model=model_name, api_key=os.getenv("GEMINI_API_KEY"))

    return model


SUMMARY_RESPONSE_TEMPLATE = PromptTemplate(
    """
    Summarize the key events of the following trip. Include the total distance, total duration, the pickup location and time, the dropoff location and time, and any significant stops like rest breaks or fuel stops. The data is in JSON format:

    {data}
  """
)
