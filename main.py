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
    # "What are the regional subsidies available in state of Maharashtra",
    # "Give me a summary of the open access regulations relevant to C&Is for Maharashtra",
    # "What are the all penalties and rebates applicable in Maharashtra (and DISCOM)?",
    "Cross subsidy surcharge and additional surcharge for open access customers in Maharashtra"
]

regulations_db = DB(db_name="maharashtra")
orders_db = DB(db_name="maharashtra_orders")

llm = LLM()

top_k = 5

for q in ques:
    queries = [ q ]
    result_1 = regulations_db.query(queries)
    result_2 = orders_db.query(queries)

    # Re Ranking for numerical data
    result = result_1 + result_2
    result = sorted(result, key=lambda x: score_numeric_richness(x), reverse=True)
    result = result[:top_k]

    context = '\n\n'.join(result)

    output = llm.ask(context, question=q)
    print(output, "\n------------------------------------------------\n")
    time.sleep(1)
