from openai import OpenAI

# because deployed locally, we use localhost:8000 and a dummy placeholder API key
client = OpenAI(base_url="http://localhost:8000/v1", api_key="FAKE_KEY") # Or use your Anyscale Service endpoint and API key   

response = client.chat.completions.create(
    model="my-llama",
    messages=[{"role": "user", "content": "Hello! What's the capital of France ?"}],
    stream=True
)

for chunk in response:
    content = chunk.choices[0].delta.content
    if content:
        print(content, end="", flush=True)