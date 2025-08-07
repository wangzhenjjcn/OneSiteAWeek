from selenium import webdriver
import requests
import json
import time

# 设置代理
chrome_options = webdriver.ChromeOptions()
# chrome_options.add_argument("--proxy-server=socks5://127.0.0.1:12345")

# 启动浏览器
driver = webdriver.Chrome(options=chrome_options)

try:
    # 打开网页
    driver.get("https://renren.com/personal/251769759/albums")
    time.sleep(5)  # 等待页面加载

    # 读取token
    token_script = "return window.frontjsConfig.token;"
    token = driver.execute_script(token_script)

    # 关闭浏览器
    driver.quit()

    # 准备请求头和URL
    headers = {
        'content-type': 'application/json',
    }
    url = 'https://api.liumingye.cn/m/api/search'

    # 定义平台和关键字
    platforms = ['YQM', 'YQD', 'YQB']
    keyword = '悬溺'

    # 准备结果文件
    with open('result.txt', 'w') as result_file:
        # 遍历每个平台
        for platform in platforms:
            # 发送OPTIONS请求
            options_response = requests.options(
                url,
                headers={
                    'Access-Control-Request-Method': 'POST',
                    'Access-Control-Request-Headers': 'content-type',
                }
            )

            # 检查OPTIONS请求是否成功
            if options_response.status_code == 200:
                # 准备POST请求的数据
                post_data = {
                    "type": platform,
                    "text": keyword,
                    "page": 1,
                    "v": "beta",
                    "_t": int(time.time() * 1000),
                    "token": f'{token}',
                }

                # 发送POST请求
                post_response = requests.post(url, headers=headers, json=post_data)
                if post_response.status_code == 200:
                    print(post_response.text)
                    result = post_response.json()
                    # 将结果写入文件
                    result_file.write(json.dumps(result, indent=4))
                    result_file.write('\n')
                else:
                    print(f'Failed to retrieve data for platform {platform}')
            else:
                print('OPTIONS request failed')

except Exception as e:
    print(f'Error: {e}')
    driver.quit()  # 确保浏览器关闭
