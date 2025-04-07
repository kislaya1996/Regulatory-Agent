import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

class Scraper:
    def __init__(self, base_url):
        self.base_url = base_url
        self.sno_description_map = {}
        self.base_dir = self.get_basedir_name()
        self.base_dir = os.path.join("downloads", self.base_dir)
        self.save_paths = set()

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def get_basedir_name(self):
        path = urlparse(self.base_url).path
        segments = path.strip("/").split("/")
        return segments[-1]

    def get_table(self):
        try:
            response = requests.get(self.base_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            return soup.find('table', {'id': 'table_tender'})
        
        except Exception as e:
            print(f"Error fetching table: {str(e)}")
            return None
        
        
    def handle_pdfurl(self, pdf_url, dir_path):
        filename = os.path.basename(pdf_url)
        save_path = os.path.join(dir_path, filename)

        if os.path.exists(save_path):
            print(f"File already exists: {filename}")
            self.save_paths.add(save_path)
        
        else:
            try:
                response = requests.get(pdf_url, stream=True)
                response.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                print(f"Downloaded: {filename} to {save_path}")
                self.save_paths.add(save_path)
            
            except Exception as e:
                print(f"Failed to download {pdf_url}: {e}")
        
    def handle_table(self, table):
        rows = table.find_all('tr')[1:]
        
        for row in rows:
            row = row.find_all('td')
            sno = row[0].text.strip()
            description = row[1].text.strip()
            
            self.sno_description_map[sno] = { "description" : description }
            
            dir_path = os.path.join(self.base_dir, sno)
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)

            pdf_links = row[2].find_all('a', href=True)
            
            for link in pdf_links:
                if link['href'].lower().endswith('.pdf'):
                    pdf_url = urljoin('https://merc.gov.in', link['href'])
                    self.handle_pdfurl(pdf_url, dir_path)


    def scrape(self):
        table = self.get_table()
        if table:
            self.handle_table(table)
        
        return self.save_paths

