import os

# import boto3
# from botocore.exceptions import ClientError
from dotenv import load_dotenv
from google import genai

load_dotenv()

class LLMGemini:
    def __init__(self):
        self.client = genai.Client(api_key="AIzaSyC295R8l9zcLFmflHzhXZHItpWVKAAB460")
        # self.client = boto3.client(
        #     "bedrock-runtime",
        #     region_name="ap-south-1",
        #     aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        #     aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        # )

        # self.model_id = "arn:aws:bedrock:ap-south-1:554902127471:inference-profile/apac.anthropic.claude-3-5-sonnet-20241022-v2:0"

    def get_prompt(self, context, question):
        prompt = f"""You are a helpful assistant that extracts information from regulatory documents. 
        
        Here is the context to analyze:
        {context}

        Based on this context, please provide answer for the following question:
        {question}

        Please format your response as only a markdown table with the following columns:
        | Charge Type | Unit | Value | Discom |
        
        If a value is marked as - or empty , include that as well. 
        """

        return prompt
    
    def ask(self, context, question):

        user_message = self.get_prompt(context, question)
        
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[user_message]
            )
            
            # Extract the response text from the correct location in the response
            response_text = response.text
            return response_text

        except Exception as e:
            print(f"ERROR: Can't invoke 'Gemini Flash 2'. Reason: {e}")
            return ""


