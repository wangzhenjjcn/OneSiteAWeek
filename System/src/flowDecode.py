import os, sys,time,time,json
import subprocess
from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

url=input('url:')
urls = set()
media_urls = set()
m3u8_urls = set()
extensions = ['.flv', '.hlv', '.f4v', '.mp4', '.mp3', '.wma', '.wav', '.m4a', '.webm', '.ogg', '.ogv', '.acc', '.mov', '.mkv', '.m3u8', '.ts']
def page_has_loaded(driver):
    return driver.execute_script("return document.readyState;") == "complete"
# 自动安装Chrome驱动
ChromeDriverManager().install()
# 启用 Chrome 的日志记录
capabilities = DesiredCapabilities.CHROME
capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
# 设置 Chrome 选项
chrome_options = Options()
# chrome_options.add_argument("--enable-logging")
chrome_options.add_argument("--log-level=3") 
chrome_options.add_argument("--headless")  # 使用 headless 模式，如果不需要可视化浏览器可以开启
# chrome_options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})
chrome_options.add_argument("--remote-debugging-port=9222")  # 这通常是为了启用性能日志记录
# 初始化webdriver
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)  # 设置隐式等待时间为10秒
# 打开目标网页
driver.get(url)  # 替换为你的目标网址
logs = driver.get_log('performance')
while not page_has_loaded(driver):
    # 等待页面加载完成
    time.sleep(1)  # 根据需要调整等待时间
    pass
for entry in logs:
    message = json.loads(entry["message"])
    message = message["message"]
    if message["method"] == "Network.requestWillBeSent":
        url = message["params"]["request"]["url"]
        urls.add(url)
# 先检查是否存在 .m3u8 链接
for url in urls:
    if url.endswith('.m3u8'):
        m3u8_urls.add(url)
# 如果存在 .m3u8 链接，则仅保留这些链接
if m3u8_urls:
    media_urls = m3u8_urls
else:
    # 否则，检查并保留所有媒体链接
    for url in urls:
        if any(url.endswith(ext) for ext in extensions):
            media_urls.add(url)
# 获取 <title> 标签的内容
title = driver.title
print("Title of the page:", title)
# 关闭浏览器
driver.quit()

# # 输出捕获到的媒体文件地址
for url in media_urls:
    # print(url)
    if("m3u8" not in url):
        # print("pass[%s]"%url)
        continue
    fileName=title+'-'+str(url).split('/')[len(str(url).split('/'))-1]
    maxThreads=32
    path=os.path.dirname(os.path.realpath(sys.argv[0]))
    programPath=path+"\\Bin\\"
    downloadFoderPath=path+"\\Download\\"
    processor=programPath+"\\cli.exe"
    command = [processor, url, "--workDir",downloadFoderPath,"--saveName",fileName,"--maxThreads",str(maxThreads),"--enableDelAfterDone","--disableDateInfo"]  #,"--proxyAddress",'http://127.0.0.1:12346'
    returnvar=subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("DONE:[%s]File:[%s]Path:[%s]"%(url,fileName,downloadFoderPath))



for i in range(0,5):
    print("All Done. Auto Close in %s secs"%(5-i))
    time.sleep(1)





