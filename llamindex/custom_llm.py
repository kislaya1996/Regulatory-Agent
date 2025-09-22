from llama_index.llms.bedrock_converse import BedrockConverse
from llama_index.llms.google_genai import GoogleGenAI
import os
# from llama_index.llms.ollama import Ollama


# llm_indexing = Ollama(model="tinyllama", request_timeout=600.0)

llm_indexing = BedrockConverse(
    model="arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.amazon.nova-lite-v1:0",
    region_name="ap-south-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0,
)

llm_retrieval = BedrockConverse(
    model="arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-sonnet-4-20250514-v1:0",
    region_name="ap-south-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0,
)

# New Gemini LLM
llm_gemini = GoogleGenAI(
    model="gemini-2.0-flash",
    api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
    temperature=0,
)


