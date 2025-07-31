from llama_index.llms.bedrock_converse import BedrockConverse
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
    model="arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0",
    region_name="ap-south-1",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    temperature=0,
)






# import os
# from llama_index.llms.google_genai import GoogleGenAI
# import time
# from utils.rate_limiter import TokenBucket # Import the TokenBucket class
# from typing import List, Any, AsyncGenerator, Generator
# from llama_index.core.llms import CompletionResponse, ChatMessage, ChatResponse, CompletionResponseGen, ChatResponseGen

# # Define rate limit: 10 RPM (requests per minute) means 10 requests / 60 seconds = 0.1666... requests per second
# RPM_LIMIT = 10
# RATE_LIMIT_CAPACITY = RPM_LIMIT  # Initial bucket size
# RATE_LIMIT_REFILL_RATE_PER_SECOND = RPM_LIMIT / 60.0 # Tokens per second

# # Initialize the rate limiter globally or within your LLM class
# llm_rate_limiter = TokenBucket(capacity=RATE_LIMIT_CAPACITY, 
#                                refill_rate_per_second=RATE_LIMIT_REFILL_RATE_PER_SECOND)

# class RateLimitedGoogleGenAI(GoogleGenAI):
#     def __init__(self, *args: Any, **kwargs: Any): # Use Any for generic args/kwargs
#         super().__init__(*args, **kwargs)
#         self._rate_limiter = llm_rate_limiter # Use the global rate limiter instance

#     def _get_api_key(self) -> str:
#         # This method is inherited, ensure it correctly gets the API key
#         # GoogleGenAI's init likely handles this already, but good to be explicit
#         return self.api_key or os.getenv("GOOGLE_GEMINI_API_KEY")

#     def _completion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
#         # Acquire a token before making the actual API call
#         self._rate_limiter.acquire() 
#         return super()._completion(prompt, **kwargs)

#     async def _acompletion(self, prompt: str, **kwargs: Any) -> CompletionResponse:
#         # Acquire a token before making the actual API call
#         self._rate_limiter.acquire() 
#         return await super()._acompletion(prompt, **kwargs)

#     # Note: _stream_complete and _astream_complete are for streaming completions
#     def _stream_completion(self, prompt: str, **kwargs: Any) -> Generator[CompletionResponse, None, None]:
#         self._rate_limiter.acquire()
#         yield from super()._stream_completion(prompt, **kwargs)

#     async def _astream_completion(self, prompt: str, **kwargs: Any) -> AsyncGenerator[CompletionResponse, None]:
#         self._rate_limiter.acquire()
#         async for x in super()._astream_completion(prompt, **kwargs):
#             yield x

#     def _chat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
#         self._rate_limiter.acquire()
#         return super()._chat(messages, **kwargs)

#     async def _achat(self, messages: List[ChatMessage], **kwargs: Any) -> ChatResponse:
#         self._rate_limiter.acquire() 
#         return await super()._achat(messages, **kwargs)

#     # Note: _stream_chat and _astream_chat are for streaming chat messages
#     def _stream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> Generator[ChatResponse, None, None]:
#         self._rate_limiter.acquire()
#         yield from super()._stream_chat(messages, **kwargs)

#     async def _astream_chat(self, messages: List[ChatMessage], **kwargs: Any) -> AsyncGenerator[ChatResponse, None]:
#         self._rate_limiter.acquire()
#         async for x in super()._astream_chat(messages, **kwargs):
#             yield x

# llm = RateLimitedGoogleGenAI(
#     model="gemini-2.0-flash",
#     api_key=os.getenv("GOOGLE_GEMINI_API_KEY"),
#     temperature=0,
# )


