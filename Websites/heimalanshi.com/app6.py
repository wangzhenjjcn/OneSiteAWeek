from selenium import webdriver
from selenium.webdriver.common.by import By
import time

def get_proxies(driver):
    print("reading")
    proxies = []
    rows = driver.find_elements(By.XPATH, '//div[@class="table_block"]/table//tr')[1:]  # Skip header
    print("reading rows:"+str(len(rows)))
    for row in rows:
        columns = row.find_elements(By.TAG_NAME, 'td')
        if len(columns) > 4:  # Ensure there are enough columns
            ip = columns[0].text
            port = columns[1].text
            proxy_type = columns[4].text
            proxies.append((ip, port, proxy_type))
    print("readed " +str(len(proxies)))
    return proxies


def save_to_file(proxies, filename):
    with open(filename, 'w') as f:
        for proxy in proxies:
            f.write(f'{proxy[0]}\t{proxy[1]}\t{proxy[2]}\n')

def main():
    driver = webdriver.Chrome()
    try:
        url = 'https://hidemy.io/en/proxy-list/'
        all_proxies = []
        
        # Pause for 20 seconds to allow user interaction
        print("Browser is open. You have 20 seconds for user interaction...")
        driver.get(url)
        time.sleep(20)
        while True:
            current_url = driver.current_url
            print('Scraping current page...')
            proxies=None
            while not proxies:
                print("try reading")
                proxies = get_proxies(driver)
                if proxies:
                    print("now have:"+str(len(proxies)))
                time.sleep(10)
            all_proxies.extend(proxies)
            print("now have:"+str(len(all_proxies)))
            save_to_file(all_proxies, 'proxies.txt')
            while driver.current_url == current_url:
                print('Waiting for user to navigate to the next page...')
                time.sleep(5)  # Check for URL change every second
            current_url = driver.current_url
            print('URL changed. Waiting for 60 seconds before scraping...')
            time.sleep(60)
        save_to_file(all_proxies, 'proxies.txt')
    finally:
        driver.quit()  # Ensure the browser is closed

if __name__ == '__main__':
    main()
