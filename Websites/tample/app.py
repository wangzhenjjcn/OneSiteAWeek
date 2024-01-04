import time
import threading
import pyautogui
import pyperclip
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys

browser_quit = False
filename = ""


def check_and_handle_dialog():
    while not browser_quit:
        time.sleep(1)
        if pyautogui.getActiveWindowTitle() == '另存为':
            pyautogui.write(filename)
            pyautogui.press('enter')

        if browser_quit:
            break


def content_click_item(driver,index):
    elements = driver.find_elements(By.CSS_SELECTOR, 'div.item.relative.rounded-md.transition-colors')
    ActionChains(driver).context_click(elements[index]).perform()

def click_item(driver,index):
    elements = driver.find_elements(By.CSS_SELECTOR, 'div.item.relative.rounded-md.transition-colors')
    ActionChains(driver).click(elements[index]).perform()

def click_download(driver):
    WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[span[text()="下载"]]/ancestor::div[@class="mx-context-menu-item-wrapper"]'))
        ).click()


def click_flac_api_download(driver):
    flac_element = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, '//div[span[contains(text(), "API写入")]]/ancestor::div[@class="arco-modal-body"]//a[contains(text(), "无损flac")]'))
        )
    ActionChains(driver).move_to_element(flac_element).click().perform()

def click_copy_filename(driver):
    global filename
    WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//div[span[text()="复制歌名"]]/ancestor::div[@class="mx-context-menu-item-wrapper"]'))
        ).click()
    filename = pyperclip.paste()
    return pyperclip.paste()

def check_all_element(driver, index):
    selector = 'div.item.relative.rounded-md.transition-colors'
    elements = driver.find_elements(By.CSS_SELECTOR, selector)
    return elements


def scroll_to_element(driver, index):
    selector = 'div.item.relative.rounded-md.transition-colors'
    while True:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        target_element = elements[index] if index < len(elements) else None
        if target_element and EC.element_to_be_clickable((By.CSS_SELECTOR, selector))(driver):
            break  
        print("Elements:[%s],index;[%s]"%(len(elements),index))
        ActionChains(driver).move_to_element(elements[0]).perform()
        ActionChains(driver).send_keys(Keys.PAGE_DOWN).perform()

def main():
    global filename
    global browser_quit

    options = webdriver.ChromeOptions()
    options.add_argument("--proxy-server=socks5://127.0.0.1:12345")

    driver = webdriver.Chrome(options=options)
    driver.get("https://tool.liumingye.cn/music/#/")
    input("Press Enter after the page has loaded...")

    while True:
        print("1.")
        print("2")
        print("3")
        print("4")
        print("5")
        print("6")
        print("7")
        print("8")
        print("9")
        print("0")
        print("q")
        print("w")
        print("e")
        print("r")
        print("a")
        print("s.earch words")
        print("d")
        print("f")
        user_option = input("Enter the keyword or 'exit' to quit: ")
        if user_option.lower() == 'exit':
            browser_quit = True
            driver.quit()
            break
        
        if (user_option.lower()=="s"):
            user_input = input("Enter the search keyword or 'exit' to quit: ")
            url = f"https://tool.liumingye.cn/music/#/search/B/song/{user_input}"
            driver.get(url)
            time.sleep(5)

        if (user_option.lower()=="a"):
            if user_option.lower() == '!!!':
                continue
            index= input("Enter the index or '!!!' to continue: ")
            index=int(index)
            print("Index:{index},ClickIndex:0")
            click_item(driver,0)
            time.sleep(2)
            scroll_to_element(driver,index)
            time.sleep(2)
            print("content click index:[%s]"%str(index))
            content_click_item(driver,index)
            time.sleep(2)
            click_copy_filename(driver)
            print("Filename:{filename}")
            time.sleep(2)
            content_click_item(driver,index)
            time.sleep(2)
            click_download(driver)
            time.sleep(2)
            
        if(user_option.lower()=="f"):
            # Click on flac
            flac_element = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, '//div[span[contains(text(), "API写入")]]/ancestor::div[@class="arco-modal-body"]//a[contains(text(), "无损flac")]'))
            )
            ActionChains(driver).move_to_element(flac_element).click().perform()

            if pyautogui.getActiveWindowTitle() == '另存为':
                pyautogui.write('C:\\Users\\YourUsername\\Music\\')
                pyautogui.press('enter')
                pyautogui.write(filename)
                pyautogui.press('enter')
     
        # if a system dialog appears
        if pyautogui.getActiveWindowTitle() == '另存为':
            pyautogui.write('C:\\Users\\YourUsername\\Music\\')
            pyautogui.press('enter')
            pyautogui.write(filename)
            pyautogui.press('enter')

        time.sleep(2)


if __name__ == "__main__":
    dialog_thread = threading.Thread(target=check_and_handle_dialog)
    dialog_thread.start()

    main()
