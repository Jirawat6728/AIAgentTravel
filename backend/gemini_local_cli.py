import os, sys, json
from dotenv import load_dotenv
from google import genai

load_dotenv(override=True)

key = os.getenv("GEMINI_API_KEY", "").strip()
model = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash").strip()  # ปรับได้
if not key:
    raise RuntimeError("GEMINI_API_KEY missing")

client = genai.Client(api_key=key)

prompt = " ".join(sys.argv[1:]).strip()
if not prompt:
    print("Usage: python gemini_local_cli.py \"your prompt\"")
    sys.exit(1)

resp = client.models.generate_content(
    model=model,
    contents=[{"role": "user", "parts": [{"text": prompt}]}],
)

# พยายามดึง text ออกมาให้ตรงไปตรงมา
text = ""
try:
    parts = resp.candidates[0].content.parts
    text = "\n".join([p.text for p in parts if getattr(p, "text", None)])
except Exception:
    text = str(resp)

print(text.strip())
