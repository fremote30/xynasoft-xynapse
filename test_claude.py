from dotenv import load_dotenv
from anthropic import Anthropic
import os

# =====================================
# LOAD ENVIRONMENT VARIABLES
# =====================================
load_dotenv()

api_key = os.getenv("ANTHROPIC_API_KEY")

print("KEY FOUND:", bool(api_key))

if not api_key:
    raise Exception(
        "ANTHROPIC_API_KEY not found"
    )

# =====================================
# CREATE CLIENT
# =====================================
client = Anthropic(
    api_key=api_key
)

# =====================================
# TEST CLAUDE
# =====================================
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=100,
    messages=[
        {
            "role": "user",
            "content": "Say hello and tell me your model name."
        }
    ]
)

# =====================================
# PRINT RESPONSE
# =====================================
print("\n===== CLAUDE RESPONSE =====\n")

for block in response.content:
    if hasattr(block, "text"):
        print(block.text)

print("\n===========================\n")