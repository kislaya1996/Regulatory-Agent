from utilities import query_discom_orders
from db import DB

discoms = ["tata","adani","msedcl"]

# orders_db = DB(db_name="orders_db", whoosh_index_dir="orders_whoosh")

for discom in discoms:
    
    print(f"Querying {discom} orders...\n")
    answer = query_discom_orders(discom)

    for k,v in answer.items():
        print(k)
        print(v)
        print("\n")
