import requests
from concurrent.futures import ThreadPoolExecutor

successful_proxies = {
    'HTTP': [],
    'SOCKS5': [],
    'SOCKS4': []
}

def test_proxy(line):
    ip, port, proxy_type = line.strip().split('\t')
    proxy_url = f"{proxy_type.lower()}://{ip}:{port}"
    proxies = {proxy_type.lower(): proxy_url}

    try:
        response = requests.get('http://www.google.com', proxies=proxies, timeout=10)
        if response.status_code == 200:
            print(f"Proxy {proxy_url} is working")
            types = proxy_type.split(", ")
            for type in types:
                successful_proxies[type].append(f"{ip}\t{port}\t{type}")
        else:
            print(f"Proxy {proxy_url} returned status code {response.status_code}")
    except Exception as e:
        print(f"Failed to connect using proxy {proxy_url}: {str(e)}")

def save_proxies():
    for type, proxies in successful_proxies.items():
        if proxies:
            filename = f"proxies_success_{type.lower()}.txt"
            with open(filename, 'w') as file:
                file.write('\n'.join(proxies))

def main():
    with open('proxies.txt', 'r') as file:
        lines = file.readlines()

    # Use a thread pool to test proxies concurrently
    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(test_proxy, lines)

    save_proxies()

if __name__ == '__main__':
    main()
