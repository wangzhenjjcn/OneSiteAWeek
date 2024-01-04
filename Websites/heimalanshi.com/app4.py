import time
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.common.exceptions import TimeoutException
import threading
import queue
import random

# List of user agents to simulate different users
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
    # ... add more user agents as needed
]

def test_proxy(proxy, proxy_type, success_lock, fail_lock):
    selenium_proxy = Proxy()
    if proxy_type == 'http':
        selenium_proxy.http_proxy = f"http://{proxy}"
        selenium_proxy.ssl_proxy = f"http://{proxy}"
    elif proxy_type == 'socks4' or proxy_type == 'socks5':
        selenium_proxy.socks_proxy = f"{proxy_type}://{proxy}"
        selenium_proxy.ssl_proxy = f"{proxy_type}://{proxy}"

    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")  # Enable incognito mode
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")  # Set random user agent
    options.proxy = selenium_proxy  # Set proxy

    driver = None
    try:
        driver = webdriver.Chrome(options=options)  # Use options parameter
        driver.set_page_load_timeout(20)  # Set page load timeout to 20 seconds
        driver.get("http://googlesz.cn")

        # Check page load state in a loop, waiting for up to 20 seconds
        for _ in range(4):
            ready_state = driver.execute_script("return document.readyState")
            if ready_state == "complete":
                break
            time.sleep(5)  # Wait for 5 seconds before checking again

        page_source = driver.page_source  # Get page source
        error_messages = ["ERR_CONNECTION_RESET", "Proxy Error", "502 Bad Gateway", "Proxy Authentication Required", "Please log in"]
        if (any(error_message in page_source for error_message in error_messages) or
                "googlesz.cn" not in driver.current_url or
                ready_state != "complete"):
            print(f"{proxy_type.upper()} proxy {proxy} is not working")
            with fail_lock:
                with open(f'{proxy_type}_fail.txt', 'a') as fail_file:
                    fail_file.write(f"{proxy}\n")
        else:
            print(f"{proxy_type.upper()} proxy {proxy} is working")
            with success_lock:
                with open(f'{proxy_type}_success.txt', 'a') as success_file:
                    success_file.write(f"{proxy}\n")
            time.sleep(60)  # Delay for 60 seconds
        driver.quit()
    except TimeoutException:
        print(f"{proxy_type.upper()} proxy {proxy} timed out")
        with fail_lock:
            with open(f'{proxy_type}_fail.txt', 'a') as fail_file:
                fail_file.write(f"{proxy}\n")
        if driver:
            driver.quit()
    except Exception as e:
        print(f"An error occurred with {proxy_type.upper()} proxy {proxy}: {e}")
        with fail_lock:
            with open(f'{proxy_type}_fail.txt', 'a') as fail_file:
                fail_file.write(f"{proxy}\n")
        if driver:
            driver.quit()

def worker(proxy_queue, proxy_type, success_lock, fail_lock):
    while not proxy_queue.empty():
        proxy = proxy_queue.get()
        test_proxy(proxy, proxy_type, success_lock, fail_lock)
        proxy_queue.task_done()

def test_proxies(proxy_file, proxy_type):
    with open(proxy_file, 'r') as file:
        proxies = file.read().splitlines()

    proxy_queue = queue.Queue()
    for proxy in proxies:
        proxy_queue.put(proxy)

    success_lock = threading.Lock()
    fail_lock = threading.Lock()

    threads = []
    for _ in range(10):  # Create 10 threads
        thread = threading.Thread(target=worker, args=(proxy_queue, proxy_type, success_lock, fail_lock))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    test_proxies('http_proxies.txt', 'http')
    test_proxies('socks4_proxies.txt', 'socks4')
    test_proxies('socks5_proxies.txt', 'socks5')
