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
    "What is cross subsidy surcharge & additional surcharge in Maharashtra for TATA discom?",
    "How much is the distribution loss/wheeling loss for commercial building connected to MSEDCL discom?",
    "How much is green energy charges in Maharashtra for consumer?"
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
    time.sleep(5)
