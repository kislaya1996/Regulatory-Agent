from db import DB
from llm import LLM
import time

ques = [
    "What are the regional subsidies available in state of Maharashtra",
    "Give me a summary of the open access regulations relevant to C&Is for Maharashtra",
    "What are the all penalties and rebates applicable in Maharashtra (and DISCOM)?",
    "Cross subsidy surcharge and additional surcharge for open access customers in Maharashtra"
]

db = DB(db_name="maharashtra")
llm = LLM()

for q in ques:
    queries = [ q ]
    result = db.query(queries)
    context = '\n\n'.join(result)

    output = llm.ask(context, question=q)
    print(output, "\n------------------------------------------------\n")
    time.sleep(1)
