from utilities import query_discom_orders
from db import DB

discoms = ["tn_combined"]

questions = [
    "What are the Energy Charges and Fixed Charges for all Low Tension (LT) consumers for 2024-25?",
    "What are the Energy Charges and Demand Charges for all High Tension (HT) consumers for 2024-25?",
    "What are the Wheeling/Network Charges for HT, LT and Overall for FY 2025-26?",
    "What is the Cross Subsidy Surcharge (CSS) for FY 2024-25?"
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
