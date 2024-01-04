import requests
from bs4 import BeautifulSoup
import csv

# Function to extract 'cili' links from a given movie page
def extract_cili_links(movie_link):
    try:
        # Send a request to the movie page
        print("get :%s"%movie_link)
        response = requests.get(movie_link)
        response.raise_for_status()

        # Parse the content of the page with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the 'cili' element
        cili_element = soup.find('table', id='cili')
        # print("cili_element :%s"%cili_element)

        # Extract all 'a' tags within the 'cili' element
        if cili_element:
            cili_links = [a['href'] for a in cili_element.find_all('a', href=True)]
            return cili_links
        else:
            return []
    except Exception as e:
        return [str(e)]

# Read the sample data from the uploaded file
sample_data_file_path = './data.csv'

# Read the links from the uploaded data.csv
sample_movie_links = []
with open(sample_data_file_path, 'r', encoding='utf-8') as file:
    reader = csv.reader(file)
    sample_movie_links = [row[0] for row in reader]


# List to hold all cili links
all_cili_links = []

# Process each movie link
for link in sample_movie_links:
    print("current:%s"%link)
    cili_links = extract_cili_links(link)
    all_cili_links.extend(cili_links)
    print("all_cili_links count:%s"%str(len(all_cili_links)))

# Save the cili links to a new CSV file
output_file_path = './data2.csv'
with open(output_file_path, 'w', newline='', encoding='utf-8') as file:
    writer = csv.writer(file)
    for link in all_cili_links:
        print("writer current:%s"%link)
        if "http" in link:
            continue
        writer.writerow([link])

output_file_path
