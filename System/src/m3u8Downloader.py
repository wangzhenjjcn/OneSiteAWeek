import os, sys,time,time,json,validators,configparser#,re,requests
import subprocess
from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


# 获取可执行文件的完整路径
executable_path = sys.argv[0]
# 获取文件名（不包含路径）
executable_name = os.path.basename(executable_path)
directory_path = os.path.dirname(os.path.abspath(executable_path))
config_file_path = directory_path+'\\config.ini'
print("Executable Name:", executable_name," By:WangZhen")
# Define the path for the config file

# Create a ConfigParser object
config = configparser.ConfigParser()

# Check if the config file exists
if not os.path.exists(config_file_path):
    print("Init Config.ini")
    # Create config file and set initial values if it doesn't exist
    config['DEFAULT'] = {
        'extensions': '.flv, .hlv, .f4v, .mp4, .mp3, .wma, .wav, .m4a, .webm, .ogg, .ogv, .acc, .mov, .mkv, .m3u8, .ts',
        'debugPort': '9222',
        'logLevel': '3',
        'useProxy': 'False',
        'socks5Proxy': 'socks5://127.0.0.1:12345',
        'httpProxy': 'http://127.0.0.1:12346',
        'proxyType' : 'socks5'
    }
    # Write the new configuration to file
    with open(config_file_path, 'w') as configfile:
        config.write(configfile)
else:
    # Read the existing config file
    print("Read the existing config file:", config_file_path," ")
    config.read(config_file_path)

# 打印 DEFAULT 节下的配置
print("DEFAULT section:")
for key in config['DEFAULT']:
    print(f"{key}: {config['DEFAULT'][key]}")

# 如果还有其他节，也可以打印出来
print("Current configuration:")
for section in config.sections():
    for key in config[section]:
        print(f"{key}: {config[section][key]}")
 
#Settings
extensions = config['DEFAULT']['extensions']
debugPort=config['DEFAULT']['debugPort']
logLevel=config['DEFAULT']['logLevel']
useProxy=config['DEFAULT']['useProxy']
socks5Proxy=config['DEFAULT']['socks5Proxy']
httpProxy=config['DEFAULT']['httpProxy']
proxyType=config['DEFAULT']['proxyType']
proxyServer=httpProxy
if(proxyType=="socks5"):
    proxyServer=socks5Proxy

url=''
# 检查是否为 PyInstaller 打包的环境
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 如果是，使用临时解压目录
    app_path = sys._MEIPASS
else:
    # 否则使用脚本所在的目录
    app_path = os.path.dirname(os.path.abspath(__file__))
while(not validators.url(url)):
    url=input('url:')
    if not validators.url(url):
        print("URL错误：%s，请重新输入"%url)        
print("URL Pass：%s"%url)
bin_path = os.path.join(app_path, 'Bin')
if not os.path.exists(bin_path):
    print("Bin Check Faild:[%s]"%bin_path)
urls = set()
media_urls = set()
m3u8_urls = set()
def page_has_loaded(driver):
    return driver.execute_script("return document.readyState;") == "complete"
# proxies = {
#     'http': 'socks5://127.0.0.1:12345',
#     'https': 'socks5://127.0.0.1:12345'
# }
# 自动安装Chrome驱动
print("Checking Chrome Driver.")
ChromeDriverManager().install()
# 启用 Chrome 的日志记录
capabilities = DesiredCapabilities.CHROME
capabilities['goog:loggingPrefs'] = {'performance': 'ALL'}
# 设置 Chrome 选项
chrome_options = Options()
# chrome_options.add_argument("--enable-logging")
# chrome_options.add_experimental_option("perfLoggingPrefs", {"enableNetwork": True})
chrome_options.add_argument("--log-level="+logLevel) 
chrome_options.add_argument("--remote-debugging-port="+debugPort)  # 这通常是为了启用性能日志记录
chrome_options.add_argument("--headless")  # 使用 headless 模式，如果不需要可视化浏览器可以开启
chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")  # 允许自动播放
chrome_options.add_argument("--mute-audio")
chrome_options.add_argument('--ignore-ssl-errors')
chrome_options.add_argument("--ignore-certificate-errors")
if useProxy==True:
    print("--proxyAddress:",proxyServer)
    chrome_options.add_argument("--proxy-server="+proxyServer) # 代理版本
# 初始化webdriver
print("Loading Chrome.")
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(10)  # 设置隐式等待时间为10秒
# 打开目标网页
print("Opening url:[%s]"%url)
driver.get(url)  # 替换为你的目标网址
print("Loaded url:[%s]"%url)
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
print("Driver exit.")
# # 输出捕获到的媒体文件地址
for url in media_urls:
    fileName=title+'-'+str(url).split('/')[len(str(url).split('/'))-1]
    maxThreads=32
    path=os.path.dirname(os.path.realpath(sys.argv[0]))
    programPath=bin_path+"\\"
    downloadFoderPath=path+"\\Download\\"
    if not os.path.exists(downloadFoderPath):
        os.makedirs(downloadFoderPath)
    processor=programPath+"\\cli.exe"
    if useProxy==True:
        print("--proxyAddress:",proxyServer)
        command = [processor, url, "--workDir",downloadFoderPath,"--saveName",fileName,"--maxThreads",str(maxThreads),"--timeOut",'20',"--retryCount",'5',"--enableDelAfterDone","--disableDateInfo","--liveRecDur","12:00:00","--enableChaCha20","--proxyAddress",proxyServer]  #,"--enableBinaryMerge"
    else:
        print("--NOproxyAddress:")
        command = [processor, url, "--workDir",downloadFoderPath,"--saveName",fileName,"--maxThreads",str(maxThreads),"--timeOut",'20',"--retryCount",'5',"--enableDelAfterDone","--disableDateInfo","--liveRecDur","12:00:00","--enableChaCha20"]  #,"--proxyAddress",'http://127.0.0.1:12346',"--enableBinaryMerge"
    print("---Downloading:[%s]File:[%s]Path:[%s]"%(url,fileName,downloadFoderPath))
    returnvar=subprocess.run(command,  stderr=subprocess.DEVNULL)
    print("-DONE:[%s]File:[%s]Path:[%s]"%(url,fileName,downloadFoderPath))
waitinput=True
while(waitinput):
    inputcheck=input("按下任意键退出，按下Y继续")
    if inputcheck=='Y' or inputcheck=='y'or inputcheck==''or inputcheck==' ':
        if executable_name.endswith('.py'):
            waitinput=False
            print("代码环境不能使用这个功能")
        else:
            newapp=subprocess.run(executable_name)
    for i in range(0,5):
        print("All Done. Auto Close in %s secs"%(5-i))
        time.sleep(1)
    waitinput=False