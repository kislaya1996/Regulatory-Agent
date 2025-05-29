from utilities import query_discom_orders
from db import DB

discoms = ["gj_ugvcl", "gj_pgvcl", "gj_mgvcl", "gj_dgvcl"]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

questions = [
    "What are the Fixed Charges, Energy Charges, Demand Charges and Reactive Energy Charges etc for all types in TARIFF SCHEDULE for LOW and MEDIUM VOLTAGE for 2024-25?",
    "What are the Fixed Charges, Energy Charges, Demand Charges, Time Of Use Charges and Rebates etc for all types in TARIFF SCHEDULE for HIGH and EXTRA HIGH TENSION for 2024-25?",
    "What are the Cross Subsidy Surcharge for FY 2024-25?",
    "What are the Wheeling Charges for FY 2024-25?",
    "What are the Distribution Losses for FY 2024-25?",
    "What is the Green Power Tariff for 2024-25?",
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
