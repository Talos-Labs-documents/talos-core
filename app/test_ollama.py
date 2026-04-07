import ollama

model = "llama3.2:3b"

response = ollama.chat(
    model=model,
    messages=[
        {
            "role": "user",
            "content": 'Return only JSON: {"steps": ["one", "two", "three"]}'
        }
    ],
)

print("FULL RESPONSE:")
print(response)
print()
print("MESSAGE CONTENT:")
print(response["message"]["content"])