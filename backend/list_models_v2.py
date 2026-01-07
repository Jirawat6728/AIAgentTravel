import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

def list_all():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("Listing models...")
    try:
        # The list method returns a generator of Model objects
        for model in client.models.list():
            print(f"Name: {model.name}")
            print(f"  Supported methods: {model.supported_methods}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_all()

