from pydantic import BaseModel
from pydantic_ai import Agent

class MyResult(BaseModel):
    name: str

try:
    agent = Agent('google-gla:gemini-1.5-pro-latest', result_type=MyResult)
    print("Success with result_type!")
except Exception as e:
    print("Failed with result_type:", e)

try:
    agent = Agent('google-gla:gemini-1.5-pro-latest', result_type=MyResult)
except Exception as e:
    print("Failed with result_type:", e)

try:
    agent = Agent('google-gla:gemini-1.5-pro-latest', output_type=MyResult)
    print("Success with output_type!")
except Exception as e:
    print("Failed with output_type:", e)
