import requests
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta

from db import DB
from llm_gemini import LLMGemini
import time
import re

def scrape_orders(url):

    save_paths = set()

    dir = os.path.join("downloads", "orders")
    if not os.path.exists(dir):
        os.makedirs(dir)

    try:
        response = requests.get(url)
        data = response.json()
        orders = data.get("data", [])
        
        for order in orders:

            # Get only 3 months earlier
            date = order.get("timestamp")
            given_date = datetime.strptime(date, "%Y%m%d")
            today = datetime.today()
            three_months_ago = today - relativedelta(months=3)

            if given_date < three_months_ago:
                print(f"Order date {given_date} is older than 3 months. Stopping.")
                break
            
            # Get only specific types
            terms = order.get("terms")
            print(terms)
            if terms != "Open Access" and terms != "Multi Year Tariff MYT":
                print(f"Order type {terms} is not Open Access or Multi Year Tariff MYT. Skipping.")
                continue

            attachments = order.get("attachment", [])
            
            for attachment in attachments:   
                
                pdf_url = attachment.get("url")
                file_name = os.path.basename(pdf_url)
                save_path = os.path.join(dir, file_name)

                if os.path.exists(save_path):
                    print(f"File already exists: {file_name}")
                    save_paths.add(save_path)

                else: 
                    try:
                        response = requests.get(pdf_url, stream=True)
                        response.raise_for_status()
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        print(f"Downloaded: {file_name} to {save_path}")
                        save_paths.add(save_path)
                    
                    except Exception as e:
                        print(f"Failed to download {pdf_url}: {e}")

        return save_paths
    
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        return None
    

def score_numeric_richness(text):
    return (
        5 * len(re.findall(r'\$\d+(?:\.\d+)?[MBK]?', text)) +  # Money values
        3 * len(re.findall(r'\d+%+', text)) +                 # Percentages
        1 * len(re.findall(r'\d+', text))                     # All other numbers
    )

def score_table_relevance(text):
    # Score based on table indicators and numeric content
    table_score = 3 if "table" in text.lower() else 0
    numeric_score = score_numeric_richness(text)
    return table_score + numeric_score

def extract_retrieval_queries(user_question, exclude_keywords=None, must_include=None):
    keywords = re.findall(r'\b[a-zA-Z0-9]+\b', user_question.lower())
    stopwords = {"the", "is", "for", "and", "as", "of", "to", "in", "on", "by", "with", "a", "an", "what"}
    keywords = [kw for kw in keywords if kw not in stopwords]
    ngrams = set()
    for n in range(1, 4):
        ngrams.update(" ".join(keywords[i:i+n]) for i in range(len(keywords)-n+1))
    ngrams.add(user_question)
    queries = list(ngrams)
    # Add must_include logic
    if must_include:
        queries = [f"{q} {must_include}" for q in queries]
    # Add exclusion logic
    if exclude_keywords:
        exclude_str = " ".join([f'NOT {kw}' for kw in exclude_keywords])
        queries = [f"{q} {exclude_str}" for q in queries]
    return queries


exclude_keywords = ["proposed", "estimated", "submitted"]
must_include = "approved"
top_k = 5

questions = [
    "What are the Fixed Charges for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What are the Energy Charges for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What is the Wheeling Charge for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What is the Wheeling Loss for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What are the CSS for HT and EHV, Industrial and Commercial consumers for 2025-26?"
]

def query_discom_orders(discom):
    
    db = DB(db_name=f"{discom}_db", whoosh_index_dir=f"{discom}_whoosh", embedding_model="BAAI/bge-large-en-v1.5")
    llm = LLMGemini()
    outputs = {}
    
    for question in questions:
        ques = extract_retrieval_queries(question, exclude_keywords=exclude_keywords, must_include=must_include)

        all_results = []
        
        for q in ques:
            
            queries = [q]

            result_chroma = db.query(queries)
            result_whoosh = db.query_whoosh(q)

            result = result_chroma + result_whoosh
            
            result = sorted(result, key=lambda x: score_table_relevance(x), reverse=True)
            result = sorted(result, key=lambda x: score_numeric_richness(x), reverse=True)
            result = result[:top_k]

            all_results.extend(result)

        context = '\n\n'.join(all_results)

        output = llm.ask(context, question=question)
        outputs[question] = output
        time.sleep(5)

    return outputs
    
