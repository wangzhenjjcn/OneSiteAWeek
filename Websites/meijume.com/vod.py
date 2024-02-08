import os, sys,time,time,json,validators,configparser#,re,requests
import subprocess
from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# 获取可执行文件的完整路径
executable_path = sys.argv[0]
# 获取文件名（不包含路径）
executable_name = os.path.basename(executable_path)
directory_path = os.path.dirname(os.path.abspath(executable_path))
# Define the path for the config file
config_file_path = directory_path+'\\config.ini'
# 检查是否为 PyInstaller 打包的环境
app_path=""
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # 如果是，使用临时解压目录
    app_path = sys._MEIPASS
else:
    # 否则使用脚本所在的目录
    app_path = os.path.dirname(os.path.abspath(__file__))
    
print("Executable Name:", executable_name,"Directory:",directory_path,"App_path:",app_path," By:WangZhen")

# Create a ConfigParser object
config = configparser.ConfigParser()

# Check if the config file exists
if not os.path.exists(config_file_path):
    print("Init Config.ini")
    # Create config file and set initial values if it doesn't exist
    config['DEFAULT'] = {
        'url':'https://m.meijume.com/',
        'keyurl':'https://m.meijume.com/vod/',
        'playurl':'https://m.meijume.com/play/',
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
url = config['DEFAULT']['url']
keyurl = config['DEFAULT']['keyurl']
debugPort=config['DEFAULT']['debugPort']
logLevel=config['DEFAULT']['logLevel']
useProxy=config['DEFAULT']['useProxy']
socks5Proxy=config['DEFAULT']['socks5Proxy']
httpProxy=config['DEFAULT']['httpProxy']
proxyType=config['DEFAULT']['proxyType']
proxyServer=httpProxy
if(proxyType=="socks5"):
    proxyServer=socks5Proxy
    
    
urls = set()
vod_urls = set()
m3u8_urls = set()
magnet_urls = set()
play_list_links=set()
playListLinks={}
h1_text=""
img_src=""

def page_has_loaded(driver):
    return driver.execute_script("return document.readyState;") == "complete"

def get_magnet_links(page_source):
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 查找所有class为"myui-panel-box"的div下的a标签
    a_tags = soup.select('.myui-panel.myui-panel-bg.clearfix a')
    # 筛选出href属性以"magnet:?"开头的链接
    magnet_links = {a['href'] for a in a_tags if a['href'].startswith('magnet:?')}
    return magnet_links

def get_magnet_links_by_a_text(page_source,link_text):
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 查找所有class为"myui-panel-box"的div下的a标签
    a_tags = soup.select('.myui-panel.myui-panel-bg.clearfix a')
    # 筛选出文本内容为"link_text"的链接，并且href属性以"magnet:?"开头
    magnet_links = {a['href'] for a in a_tags if a.text.strip() == link_text and a['href'].startswith('magnet:?')}
    return magnet_links

def get_playListLinks(page_source,page_url):
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 寻找所有id以playlist开头的div
    playlist_divs = soup.find_all('div', id=lambda x: x and x.startswith('playlist'))
    # 初始化一个字典来存储id和对应的href集合
    playlist_links = {}
    for div in playlist_divs:
        ul = div.find('ul')  # 在每个div中寻找ul
        if ul:  # 如果找到ul
            a_tags = ul.find_all('a', href=lambda x: x and x.startswith('/play/'))
            # 使用urljoin把href转换为完整的URL地址
            full_urls = [urljoin(page_url, a['href']) for a in a_tags]
            playlist_links[div['id']] = full_urls
    return playlist_links


def get_h1_text(page_source):
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 寻找class为"title text-fff"的h1标签
    h1_tag = soup.find('h1', class_='title text-fff')
    # 获取h1标签的文本内容
    h1_text = h1_tag.text.strip() if h1_tag else "H1 tag not found"
    return h1_text

def get_img_src(page_source,page_url):
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 寻找class为"title text-fff"的h1标签
    # 寻找class为"myui-content__thumb"的div下的第一个img标签
    div = soup.find('div', class_='myui-content__thumb')
    if div:
        img_tag = div.find('img')
        if img_tag and img_tag.has_attr('original'):
            # 使用urljoin确保得到完整的链接地址
            original_src = urljoin(page_url, img_tag['original'])
            return original_src
        if img_tag and img_tag.has_attr('src'):
            # 使用urljoin确保得到完整的链接地址
            img_src = urljoin(page_url, img_tag['src'])
            return img_src
        else:
            return "IMG tag not found or missing SRC attribute"
    else:
        return "DIV with class 'myui-content__thumb' not found"


url="https://m.meijume.com/vod/meiju21891.html"
 
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
        murl = message["params"]["request"]["url"]
        urls.add(murl)
# 先检查是否存在 .m3u8 链接
for urlm3u8 in urls:
    if urlm3u8.endswith('.m3u8'):
        m3u8_urls.add(urlm3u8)
# 如果存在 .m3u8 链接，则仅保留这些链接
if m3u8_urls:
    media_urls = m3u8_urls
else:
    pagesource=driver.page_source
    h1_text=get_h1_text(pagesource)
    magnet_links=get_magnet_links_by_a_text(pagesource,'本地下载')
    playListLinks=get_playListLinks(pagesource,url)
    for ml in magnet_links:
        magnet_urls.add(ml)
    img_src=get_img_src(pagesource,url)
# 获取 <title> 标签的内容
title = h1_text
print("Title of the page:", title)
# 关闭浏览器
driver.quit()
print("Driver exit.")


for mml in magnet_urls:
    print("magnet_urls:",mml)
print("==================================")
for pln in playListLinks:
    print("Plsylist:",pln)
    for pll in playListLinks[pln]:
        print("play_list_links:",pll)
    print("=======================")
print("==================================")
print("imgsrc:",img_src)
print("==================================")
print("h1_text:",h1_text)





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