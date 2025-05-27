from utilities import query_discom_orders
from db import DB

discoms = ["gj_surat", "gj_ahembdabad"]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

questions = [
    "What are the Fixed Charges, Energy Charges, Demand Charges and Reactive Energy Charges for all types in RATE SCHEDULE for LOW/MEDIUM TENSION for 2024-25?",
    "What are the Fixed Charges, Energy Charges, Demand Charges, Time Of Use Charges and Rebates for all types in RATE SCHEDULE for HIGH TENSION for 2024-25?",
    "What is the Green Power Tariff for 2024-25?"
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
