import os

import boto3
from botocore.exceptions import ClientError

from dotenv import load_dotenv
load_dotenv()

class LLM:
    def __init__(self):
        
        self.client = boto3.client(
            "bedrock-runtime",
            region_name="ap-south-1",
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )

        self.model_id = "arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0"

    def get_prompt(self, context, question):

        prompt = f"""
            Based of the following context:
            {context}

            Answer the following question:
            {question}
            Give very precise answers, no need to explain details not relevant to the question. If the question demands looking at values, just provide the value.
        """

        return prompt
    
    def ask(self, context, question):

        user_message = self.get_prompt(context, question)
        conversation = [
            {
                "role": "user",
                "content": [{"text": user_message}],
            }
        ]

        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=conversation,
            )

            response_text = response["output"]["message"]["content"][0]["text"]
            return response_text

        except (ClientError, Exception) as e:
            print(f"ERROR: Can't invoke '{self.model_id}'. Reason: {e}")
            return ""


