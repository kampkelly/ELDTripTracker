import os

from dotenv import load_dotenv
from llama_index.core.prompts import PromptTemplate
from llama_index.llms.gemini import Gemini

load_dotenv()


def get_llm(model_name="models/gemini-1.5-flash"):
    model = Gemini(model=model_name, api_key=os.getenv("GEMINI_API_KEY"))

    return model


SUMMARY_RESPONSE_TEMPLATE = PromptTemplate(
    """
        Summarize the key events of the following trip. Include the total distance, total duration,
        the pickup location and time, the dropoff location and time, and any significant stops like rest breaks
        or fuel stops. The data is in JSON format:

    Example response:
    This trip covered a total distance of 1414.13 miles and lasted 26.33 hours.  It began at Chicago on
    March 23, 2025, 19:27:38 and ended at Miami on March 24, 2025, 19:27:38.

      The trip included the following significant stops:

      * **Pickup:** at 2025-03-22T19:18:53.652224Z (duration: 1 hour)
      * **Rest Break:** at 2025-03-23T04:08:08.578394Z (duration: 30 minutes)
      * **Fuel Stop:** at 2025-03-23T09:46:48.411762Z (duration: 30 minutes)
      * **Mandatory 70 hour Rest Break:** at 2025-03-23T13:08:08.581216Z (duration: 34 hours)
      * **Dropoff:** at 2025-03-23T19:27:38.857738Z (duration: 1 hour)


      The ELD logs indicate 207.72 miles driven on March 22nd and 964.80 miles driven on March 23rd.

      Now do for the following data (format all the dates to be readable like March 23, 2025, 19:27:38 UTC):
      Use these for start location, start time, end location andend time respectively: {start_location}, {start_time},
      {end_location}, dropoff timestamp in data

    {data}
  """
)
