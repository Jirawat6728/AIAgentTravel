import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv(override=True)

def list_legacy():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    print(f"Legacy Listing with Key: {api_key[:10]}...")
    try:
        for m in genai.list_models():
            print(f"Name: {m.name}")
            print(f"  Methods: {m.supported_generation_methods}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_legacy()

