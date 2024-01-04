import requests
from bs4 import BeautifulSoup
import csv

def get_movie_links(url):
    try:
        # Send a request to the website
        response = requests.get(url)
        response.raise_for_status()

        # Parse the content of the page with BeautifulSoup
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all links on the page
        links = soup.find_all('a', href=True)

        # Filter out the links that start with 'https://www.yinfans.net/movie/'
        movie_links = [link['href'] for link in links if link['href'].startswith('https://www.yinfans.net/movie/')]

        return movie_links
    except Exception as e:
        return str(e)

# URL of the website to scrape
url = 'https://www.yinfans.net/'

# Get movie links
movie_links = get_movie_links(url)

# Check if the result is a list of links or an error message
if isinstance(movie_links, list):
    # Save the links to a CSV file
    with open('data.csv', 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for link in movie_links:
            writer.writerow([link])
else:
    # Handle errors
    print("Error occurred:", movie_links)
