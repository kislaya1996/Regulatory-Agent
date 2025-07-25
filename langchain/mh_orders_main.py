from utilities import query_discom_orders
from db import DB

discoms = ["adani",
           "msedcl", 
           "tata" ]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

questions = [
    "What are the Fixed Charges for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What are the Energy Charges for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What is the Wheeling Charge for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What is the Wheeling Loss for HT and EHV, Industrial and Commercial consumers for 2025-26?",
    "What are the CSS for HT and EHV, Industrial and Commercial consumers for 2025-26?"
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
