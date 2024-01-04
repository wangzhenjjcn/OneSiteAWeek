from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.proxy import Proxy, ProxyType
import time

def get_proxies(driver):
    proxies = []
    rows = driver.find_elements(By.XPATH, '//div[@class="table_block"]/table//tr')[1:]  # Skip header
    for row in rows:
        columns = row.find_elements(By.TAG_NAME, 'td')
        if len(columns) > 4:  # Ensure there are enough columns
            ip = columns[0].text
            port = columns[1].text
            proxy_type = columns[4].text
            proxies.append((ip, port, proxy_type))
    return proxies

def save_to_file(proxies, filename):
    with open(filename, 'w') as f:
        for proxy in proxies:
            f.write(f'{proxy[0]}\t{proxy[1]}\t{proxy[2]}\n')

def main():
    proxy = Proxy({
        'proxyType': 'MANUAL',
        'socksProxy': '127.0.0.1:12345'
    })

    chrome_options = webdriver.ChromeOptions()
    chrome_options.headless = True
    chrome_options.proxy = proxy

    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = 'https://hidemy.io/en/proxy-list/'
        all_proxies = []

        print("Browser is open. You have 20 seconds for user interaction...")
        time.sleep(20)

        # rest of your code...


        # Pause for 20 seconds to allow user interaction
        print("Browser is open. You have 20 seconds for user interaction...")
        time.sleep(20)

        while True:
            driver.get(url)
            time.sleep(2)  # Allow the page to load

            if check_for_cloudflare(driver):
                print("Cloudflare check encountered. Waiting for 10 minutes before retrying...")
                time.sleep(600)  # Wait for 10 minutes before retrying
                continue  # Go back to the start of the loop

            print('Scraping current page...')
            proxies = get_proxies(driver)
            while not proxies:
                proxies = get_proxies(driver)
                time.sleep(10)
                # break  # Exit the loop if there are no more proxies
            all_proxies.extend(proxies)
            save_to_file(all_proxies, 'proxies.txt')
            print('Waiting for user to navigate to the next page...')
            current_url = driver.current_url
            num=0
            while driver.current_url == current_url:
                num+=1
                time.sleep(10)  # Check for URL change every second
                if num>300:
                    break
            if num>299:
                break
            print('URL changed. Waiting for 5 seconds before scraping...')
            time.sleep(5)
        save_to_file(all_proxies, 'proxies.txt')

    finally:
        driver.quit()

if __name__ == '__main__':
    main()
