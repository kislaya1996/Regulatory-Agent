from utilities import query_discom_orders
from db import DB

discoms = ["karnataka_combined"]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

questions = [
    "What are the Fixed Charges for Industrial (HT-2(a)) and Commercial (HT-2(b)) consumers for 2025-26?",
    "What are the Energy Charges for Industrial (HT-2(a)) and Commercial (HT-2(b)) consumers for 2025-26?",
    "What are the Wheeling Charges for consumers (all DISCOMs) for 2025-26?",
    "What are the Distribution Losses for consumers (all DISCOMs) for 2025-26?",
    "What are the CSS for Industrial (HT-2(a)) and Commercial (HT-2(b)) consumers for 2025-26?",
    "What are the Green Tariffs for consumers (all DISCOMs) for 2025-26?"
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
