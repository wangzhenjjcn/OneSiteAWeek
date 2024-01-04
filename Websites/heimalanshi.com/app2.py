import requests
import threading
import queue

def test_proxy(proxy, success_lock, fail_lock):
    proxy_dict = {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }
    try:
        response = requests.get("http://googlesz.cn", proxies=proxy_dict, timeout=15, allow_redirects=False)
        if response.status_code == 200 and not response.history:
            print(f"Proxy {proxy} is working")
            with success_lock:
                with open('success.txt', 'a') as success_file:
                    success_file.write(f"{proxy}\n")
        else:
            print(f"Proxy {proxy} is not working")
            with fail_lock:
                with open('fail.txt', 'a') as fail_file:
                    fail_file.write(f"{proxy}\n")
    except Exception as e:
        print(f"An error occurred with proxy {proxy}: {e}")
        with fail_lock:
            with open('fail.txt', 'a') as fail_file:
                fail_file.write(f"{proxy}\n")

def worker(proxy_queue, success_lock, fail_lock):
    while not proxy_queue.empty():
        proxy = proxy_queue.get()
        test_proxy(proxy, success_lock, fail_lock)
        proxy_queue.task_done()

def test_proxies():
    with open('http_proxies.txt', 'r') as file:
        proxies = file.read().splitlines()

    proxy_queue = queue.Queue()
    for proxy in proxies:
        proxy_queue.put(proxy)

    success_lock = threading.Lock()
    fail_lock = threading.Lock()

    threads = []
    for _ in range(80):  # 创建10个线程
        thread = threading.Thread(target=worker, args=(proxy_queue, success_lock, fail_lock))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

if __name__ == "__main__":
    test_proxies()
