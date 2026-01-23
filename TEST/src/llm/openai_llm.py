import os
from dotenv import load_dotenv
from openai import OpenAI

# Load .env once
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY not found in environment")

client = OpenAI(api_key=OPENAI_API_KEY)


def call_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.9,
    )

    return response.choices[0].message.content.strip()
