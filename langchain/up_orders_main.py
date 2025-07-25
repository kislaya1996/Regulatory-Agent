from utilities import query_discom_orders
from db import DB

discoms = ["up_combined"]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

questions = [
    "What are the payable Fixed Charges, Energy Charges and Demand Charges for all LMV consumers for 2023-24?",
    "What are the payable Fixed Charges, Energy Charges and Demand Charges for all HV consumers for 2023-24?",
    "What are the Fixed Charges, Energy Charges and Demand Charges (excluging subsidy) for all LMV consumers for 2023-24?",
    "What are the Fixed Charges, Energy Charges and Demand Charges (excluging subsidy) for all HV consumers for 2023-24?",
    "What is the Subsidy/Cross Subsidy for all LMV consumers for 2023-24?",
    "What is the Subsidy/Cross Subsidy for all HV consumers for 2023-24?"
]

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom, questions)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
