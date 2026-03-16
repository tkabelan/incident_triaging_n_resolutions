from openai import OpenAI

client = OpenAI(api_key="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")

response = client.responses.create(
    model="gpt-5.4",
    input="Hello"
)

print(response.output_text)