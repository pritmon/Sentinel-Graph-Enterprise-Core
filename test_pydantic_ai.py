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
    agent = Agent('google-gla:gemini-1.5-pro-latest', deps_type=MyResult)
    print("Success with deps_type!")
except Exception as e:
    print("Failed with deps_type:", e)

