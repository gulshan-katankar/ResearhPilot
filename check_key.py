from dotenv import load_dotenv
import os

load_dotenv(override=True)

from langchain_google_genai import ChatGoogleGenerativeAI

# Test 1: pass via api_key param
try:
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0,
        max_tokens=10,
    )
    result = llm.invoke("Say hello")
    print("SUCCESS with api_key param:", result.content)
except Exception as e:
    print(f"FAILED with api_key param: {e}")

# Test 2: rely on env var only (no explicit key)
try:
    llm2 = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        temperature=0,
        max_tokens=10,
    )
    result2 = llm2.invoke("Say hello")
    print("SUCCESS with env var only:", result2.content)
except Exception as e:
    print(f"FAILED with env var only: {e}")
