import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")
base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

print(f"Testing DeepSeek API...")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
print(f"API Key starts with: {api_key[:5]}..." if api_key else "API Key not found!")

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, this is a test."},
        ],
        stream=False
    )
    print("\n✅ Connection Successful!")
    print(f"Response: {response.choices[0].message.content}")
except Exception as e:
    print(f"\n❌ Connection Failed!")
    print(f"Error: {str(e)}")
