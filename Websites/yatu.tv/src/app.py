#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, sys,re,time,urllib,lxml,threading,time,requests,base64,json,ast
import http.cookiejar as cookielib
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
import subprocess
import platform
import hashlib
from flask import Flask

yatuAddress='http://www.yatu.tv:2082/'

def getLastPage(linkAddress):
    header = {
            'User-Agent': 'Mozilla/5.0 (iPod; CPU iPhone OS 14_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                          'like Gecko) CriOS/87.0.4280.163 Mobile/15E148 Safari/604.1',
        }
    param = {
            
        }
    url= linkAddress
    
    with requests.Session() as s:
        res = s.get(url, headers=header, params=param).json()
    
    # response = requests.get(url, stream=True)
    # response.raise_for_status() 


def main():
    getLastPage(yatuAddress)

if __name__ == "__main__":
    main()
