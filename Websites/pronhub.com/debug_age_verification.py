#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试年龄验证功能
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import PornhubScraper
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def debug_age_verification():
    """详细调试年龄验证功能"""
    print("=== 详细调试年龄验证功能 ===")
    
    scraper = PornhubScraper(use_selenium=True)
    
    try:
        scraper.init_selenium_driver()
        
        if not scraper.driver:
            print("❌ Selenium初始化失败")
            return
        
        # 访问测试页面
        test_url = "https://www.pornhub.com/video/search?search=test"
        print(f"访问页面: {test_url}")
        
        scraper.driver.get(test_url)
        time.sleep(5)  # 等待页面加载
        
        # 检查页面源码
        page_source = scraper.driver.page_source
        print(f"页面源码长度: {len(page_source)}")
        
        # 检查是否有年龄验证模态框
        try:
            modal = scraper.driver.find_element(By.ID, "js-ageDisclaimerModal")
            print("✓ 找到年龄验证模态框")
            
            # 打印模态框的HTML
            modal_html = modal.get_attribute('outerHTML')
            print(f"模态框HTML: {modal_html[:500]}...")
            
            # 查找所有按钮
            buttons = scraper.driver.find_elements(By.TAG_NAME, "button")
            print(f"找到 {len(buttons)} 个按钮")
            
            for i, button in enumerate(buttons):
                try:
                    button_text = button.text.strip()
                    button_classes = button.get_attribute('class')
                    button_id = button.get_attribute('id')
                    
                    print(f"按钮 {i+1}: 文本='{button_text}', 类='{button_classes}', ID='{button_id}'")
                    
                    if any(keyword in button_text for keyword in ['18', '我年满', '满十八', '输入']):
                        print(f"*** 匹配到年龄验证按钮: '{button_text}' ***")
                        
                        # 检查按钮状态
                        is_displayed = button.is_displayed()
                        is_enabled = button.is_enabled()
                        print(f"按钮状态: displayed={is_displayed}, enabled={is_enabled}")
                        
                        if is_displayed and is_enabled:
                            print("尝试点击按钮...")
                            
                            # 方法1: 直接点击
                            try:
                                button.click()
                                print("✓ 直接点击成功")
                            except Exception as e1:
                                print(f"直接点击失败: {e1}")
                                
                                # 方法2: JavaScript点击
                                try:
                                    scraper.driver.execute_script("arguments[0].click();", button)
                                    print("✓ JavaScript点击成功")
                                except Exception as e2:
                                    print(f"JavaScript点击失败: {e2}")
                                    
                                    # 方法3: 滚动后点击
                                    try:
                                        scraper.driver.execute_script("arguments[0].scrollIntoView(true);", button)
                                        time.sleep(1)
                                        button.click()
                                        print("✓ 滚动后点击成功")
                                    except Exception as e3:
                                        print(f"滚动后点击失败: {e3}")
                            
                            # 等待并检查模态框是否消失
                            time.sleep(2)
                            try:
                                scraper.driver.find_element(By.ID, "js-ageDisclaimerModal")
                                print("⚠️  模态框仍然存在")
                            except:
                                print("✓ 模态框已消失")
                                return True
                        else:
                            print("按钮不可见或不可点击")
                            
                except Exception as e:
                    print(f"处理按钮 {i+1} 时出错: {e}")
                    continue
            
            print("未找到可点击的年龄验证按钮")
            return False
            
        except Exception as e:
            print(f"查找模态框时出错: {e}")
            return False
            
    except Exception as e:
        print(f"调试过程中出错: {e}")
        return False
    finally:
        scraper.close_driver()

def test_xpath_method():
    """测试XPath方法"""
    print("\n=== 测试XPath方法 ===")
    
    scraper = PornhubScraper(use_selenium=True)
    
    try:
        scraper.init_selenium_driver()
        
        test_url = "https://www.pornhub.com/video/search?search=test"
        scraper.driver.get(test_url)
        time.sleep(5)
        
        # 等待模态框出现
        try:
            modal = WebDriverWait(scraper.driver, 10).until(
                EC.presence_of_element_located((By.ID, "js-ageDisclaimerModal"))
            )
            print("✓ 模态框出现")
            
            # 尝试XPath查找按钮
            try:
                age_button = WebDriverWait(scraper.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '我年满 18 岁') or contains(text(), '输入')]"))
                )
                
                print(f"✓ 通过XPath找到按钮: '{age_button.text}'")
                
                # 点击按钮
                age_button.click()
                print("✓ XPath方法点击成功")
                
                # 等待模态框消失
                try:
                    WebDriverWait(scraper.driver, 5).until(
                        EC.invisibility_of_element_located((By.ID, "js-ageDisclaimerModal"))
                    )
                    print("✓ 模态框已消失，XPath方法成功")
                    return True
                except:
                    print("⚠️  模态框未消失")
                    return False
                    
            except Exception as e:
                print(f"XPath方法失败: {e}")
                return False
                
        except Exception as e:
            print(f"等待模态框时出错: {e}")
            return False
            
    except Exception as e:
        print(f"XPath测试出错: {e}")
        return False
    finally:
        scraper.close_driver()

if __name__ == "__main__":
    print("开始详细调试年龄验证功能...")
    
    # 调试1: 详细分析
    result1 = debug_age_verification()
    
    # 调试2: XPath方法测试
    result2 = test_xpath_method()
    
    print(f"\n=== 调试结果 ===")
    print(f"详细分析: {'✓ 成功' if result1 else '❌ 失败'}")
    print(f"XPath方法: {'✓ 成功' if result2 else '❌ 失败'}") 