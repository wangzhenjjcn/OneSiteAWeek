from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.chrome.options import Options
import time

def save_to_file(filename, data):
    with open(filename, 'a') as file:
        file.write(data + '\n')

def test_proxies():
    with open('http_proxies.txt', 'r') as file:
        proxies = file.read().splitlines()

    for proxy in proxies:
        print(f"Testing proxy: {proxy}")
        try:
            chrome_options = Options()
            chrome_options.add_argument(f"--proxy-server=http://{proxy}")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get("http://googlesz.cn")
            
            time.sleep(5)
            
            if "googlesz.cn" in driver.current_url:
                print(f"Proxy {proxy} is working")
                save_to_file('success.txt', proxy)
            else:
                print(f"Proxy {proxy} is not working")
                save_to_file('fail.txt', proxy)

            driver.quit()

        except Exception as e:
            print(f"An error occurred: {e}")
            save_to_file('fail.txt', proxy)
            continue

if __name__ == "__main__":
    test_proxies()
