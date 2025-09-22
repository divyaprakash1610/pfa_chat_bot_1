from groq import Groq
import os
import config

# Initialize Groq client once
client = Groq(api_key=config.GROQ_API_KEY)

def call_llm_api(messages, model="openai/gpt-oss-20b"):
    print("Calling Groq LLM API...")
    """
    messages: list of dicts like [{"role": "user", "content": "Hello"}]
    model: Groq LLM model
    """
    # Groq API expects the same chat format
    response = client.chat.completions.create(
        messages=messages,
        model=model
    )
    # Extract the assistant reply
    return response.choices[0].message.content
