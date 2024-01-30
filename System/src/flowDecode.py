
import time
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import json  

# 自动安装Chrome驱动
ChromeDriverManager().install()

# 启用浏览器的网络日志记录
caps = DesiredCapabilities.CHROME
caps['goog:loggingPrefs'] = {'performance': 'ALL'}

# 初始化webdriver
driver = webdriver.Chrome( )

# 打开目标网页

# url = 'video61463221/_'
url='/m031358/play1-344.html'
driver.get(url)  # 替换为你的目标网址

# 等待页面加载完成
time.sleep(10)  # 根据需要调整等待时间

# 提取网络日志
logs = driver.get_log('performance')
media_urls = set()

for log in logs:
    log_json = json.loads(log['message'])['message']
    if 'Network.responseReceived' in log_json['method']:
        # 检查日志中是否有'response'字段
        if 'response' in log_json['params']:
            response = log_json['params']['response']
            url = response['url']
            mime_type = response['mimeType']
            # 检查MIME类型和文件扩展名
            if any(url.endswith(ext) for ext in ['.flv', '.hlv', '.f4v', '.mp4', '.mp3', '.wma', '.wav', '.m4a', '.webm', '.ogg', '.ogv', '.acc', '.mov', '.mkv', '.m3u8', '.ts']) and (mime_type.startswith('video/') or mime_type.startswith('audio/')):
                media_urls.add(url)

# 输出捕获到的媒体文件地址
for url in media_urls:
    print(url)

# 关闭浏览器
driver.quit()
