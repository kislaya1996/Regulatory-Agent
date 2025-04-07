import requests
import os
import re

def scrape_orders(url):

    save_paths = set()

    dir = os.path.join("downloads", "orders")
    if not os.path.exists(dir):
        os.makedirs(dir)

    try:
        response = requests.get(url)
        data = response.json()
        orders = data.get("data", [])
        
        for order in orders:
            
            attachments = order.get("attachment", [])
            
            for attachment in attachments:   
                
                pdf_url = attachment.get("url")
                file_name = os.path.basename(pdf_url)
                save_path = os.path.join(dir, file_name)

                if os.path.exists(save_path):
                    print(f"File already exists: {file_name}")
                    save_paths.add(save_path)

                else: 
                    try:
                        response = requests.get(pdf_url, stream=True)
                        response.raise_for_status()
                        with open(save_path, 'wb') as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        print(f"Downloaded: {file_name} to {save_path}")
                        save_paths.add(save_path)
                    
                    except Exception as e:
                        print(f"Failed to download {pdf_url}: {e}")

        return save_paths
    
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        return None
