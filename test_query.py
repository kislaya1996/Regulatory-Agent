from db import DB
from llm import LLM
import time
import re

def score_numeric_richness(text):
    return (
        5 * len(re.findall(r'\$\d+(?:\.\d+)?[MBK]?', text)) +  # Money values
        3 * len(re.findall(r'\d+%+', text)) +                 # Percentages
        1 * len(re.findall(r'\d+', text))                     # All other numbers
    )

ques = [
    # "What is cross subsidy surcharge for industrial customer for FY 2024-2025?",
    "What are HT tariff categories and their energy charges for Fy 23 & Fy24?",
    "What is the wheeling loss & wheeling charges for all type of connections?"
]

db = DB(db_name="test_db", whoosh_index_dir="test_whoosh", embedding_model="BAAI/bge-large-en-v1.5")
llm = LLM()

top_k = 5

for q in ques:
    queries = [ q ]
    result_db = db.query(queries)
    result_whoosh = db.query_whoosh(q)

    result = result_db + result_whoosh

    # Re Ranking for numerical data
    result = sorted(result, key=lambda x: score_numeric_richness(x), reverse=True)
    result = result[:top_k]

    context = '\n\n'.join(result)

    output = llm.ask(context, question=q)
    print(output, "\n------------------------------------------------\n")
    time.sleep(5)
