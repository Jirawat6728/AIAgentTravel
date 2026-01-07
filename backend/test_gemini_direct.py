import os
import asyncio
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

async def test_gen():
    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash-latest")
    
    if not api_key:
        print("GEMINI_API_KEY not found")
        return
        
    client = genai.Client(api_key=api_key)
    print(f"Testing Model: {model_name}")
    print(f"With Key: {api_key[:10]}...")
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents="Say 'System is online' and nothing else."
        )
        print("\nResponse:")
        # Force encoding for Windows terminal if needed
        print(response.text.encode('ascii', 'ignore').decode('ascii'))
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    asyncio.run(test_gen())

