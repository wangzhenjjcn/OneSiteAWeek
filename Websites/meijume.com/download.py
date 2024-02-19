#!/usr/bin/env python
#-*- coding:utf-8 -*-
import os, sys,time,time,json,validators,configparser#,re,requests
import requests,threading

from io import BytesIO
import subprocess
from selenium import webdriver 
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from urllib.parse import urljoin
try:
    from tkinter import *
except ImportError:  #Python 2.x
    PythonVersion = 2
    from Tkinter import *
    from tkFont import Font
    from ttk import *
    #Usage:showinfo/warning/error,askquestion/okcancel/yesno/retrycancel
    from tkMessageBox import *
    #Usage:f=tkFileDialog.askopenfilename(initialdir='E:/Python')
    #import tkFileDialog
    #import tkSimpleDialog
else:  #Python 3.x
    PythonVersion = 3
    from tkinter.font import Font
    from tkinter.ttk import *
    from tkinter.messagebox import *
    #import tkinter.filedialog as tkFileDialog
    #import tkinter.simpledialog as tkSimpleDialog    #askstring()

from PIL import Image, ImageTk

class Application_ui(Frame):
    #这个类仅实现界面生成功能，具体事件处理代码在子类Application中。
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master.title('影视下载')
        self.master.geometry('1550x850')
        self.createWidgets()

    def createWidgets(self):
        self.top = self.winfo_toplevel()

        self.style = Style()

        self.style.configure('FrameDetial.TLabelframe',font=('宋体',9))
        self.FrameDetial = LabelFrame(self.top, text='影片详情', style='FrameDetial.TLabelframe')
        self.FrameDetial.place(relx=0.408, rely=0.009, relwidth=0.579, relheight=0.971)

        self.style.configure('FrameSearchResault.TLabelframe',font=('宋体',9))
        self.FrameSearchResault = LabelFrame(self.top, text='检索结果', style='FrameSearchResault.TLabelframe')
        self.FrameSearchResault.place(relx=0.005, rely=0.104, relwidth=0.393, relheight=0.876)

        self.style.configure('FrameSearch.TLabelframe',font=('宋体',9))
        self.FrameSearch = LabelFrame(self.top, text='检索影视', style='FrameSearch.TLabelframe')
        self.FrameSearch.place(relx=0.005, rely=0.009, relwidth=0.393, relheight=0.086)

        self.ComboDetialTypeList = ['解析后显示',]
        self.ComboDetialType = Combobox(self.FrameDetial, values=self.ComboDetialTypeList, font=('宋体',9))
        self.ComboDetialType.place(relx=0.187, rely=0.145, relwidth=0.492, relheight=0.024)
        self.ComboDetialType.set(self.ComboDetialTypeList[0])

        self.style.configure('CommandCopyListMag.TButton',font=('宋体',9))
        self.CommandCopyListMag = Button(self.FrameDetial, text='拷贝磁链', command=self.CommandCopyListMag_Cmd, style='CommandCopyListMag.TButton')
        self.CommandCopyListMag.place(relx=0.731, rely=0.349, relwidth=0.179, relheight=0.05)

        self.style.configure('CommandDownloadAllList.TButton',font=('宋体',9))
        self.CommandDownloadAllList = Button(self.FrameDetial, text='下载所有', command=self.CommandDownloadAllList_Cmd, style='CommandDownloadAllList.TButton')
        self.CommandDownloadAllList.place(relx=0.731, rely=0.281, relwidth=0.179, relheight=0.05)

        self.style.configure('CommandDownloadSelected.TButton',font=('宋体',9))
        self.CommandDownloadSelected = Button(self.FrameDetial, text='下载选中', command=self.CommandDownloadSelected_Cmd, style='CommandDownloadSelected.TButton')
        self.CommandDownloadSelected.place(relx=0.731, rely=0.213, relwidth=0.179, relheight=0.05)

        self.style.configure('CommandDetialOpenEpisodes.TButton',font=('宋体',9))
        self.CommandDetialOpenEpisodes = Button(self.FrameDetial, text='打开播放', command=self.CommandDetialOpenEpisodes_Cmd, style='CommandDetialOpenEpisodes.TButton')
        self.CommandDetialOpenEpisodes.place(relx=0.812, rely=0.078, relwidth=0.179, relheight=0.05)

        self.style.configure('CommandDetialDownloadAllEpisodes.TButton',font=('宋体',9))
        self.CommandDetialDownloadAllEpisodes = Button(self.FrameDetial, text='下载所有', command=self.CommandDetialDownloadAllEpisodes_Cmd, style='CommandDetialDownloadAllEpisodes.TButton')
        self.CommandDetialDownloadAllEpisodes.place(relx=0.624, rely=0.078, relwidth=0.179, relheight=0.05)

        self.ListDownloadSourceVar = StringVar(value='解析后显示')
        self.ListDownloadSourceFont = Font(font=('宋体',9))
        self.ListDownloadSource = Listbox(self.FrameDetial, listvariable=self.ListDownloadSourceVar, font=self.ListDownloadSourceFont)
        self.ListDownloadSource.place(relx=0.071, rely=0.213, relwidth=0.608, relheight=0.558)

        self.style.configure('CommandDetialDownloadCurrentEpisodes.TButton',font=('宋体',9))
        self.CommandDetialDownloadCurrentEpisodes = Button(self.FrameDetial, text='下载当前', command=self.CommandDetialDownloadCurrentEpisodes_Cmd, style='CommandDetialDownloadCurrentEpisodes.TButton')
        self.CommandDetialDownloadCurrentEpisodes.place(relx=0.437, rely=0.078, relwidth=0.176, relheight=0.05)

        self.ComboDetialPlaySourceEpisodesList = ['解析后显示',]
        self.ComboDetialPlaySourceEpisodes = Combobox(self.FrameDetial, values=self.ComboDetialPlaySourceEpisodesList, font=('宋体',9))
        self.ComboDetialPlaySourceEpisodes.place(relx=0.187, rely=0.107, relwidth=0.171, relheight=0.024)
        self.ComboDetialPlaySourceEpisodes.set(self.ComboDetialPlaySourceEpisodesList[0])

        self.ComboDetialPlaySourceList = ['解析后显示',]
        self.ComboDetialPlaySource = Combobox(self.FrameDetial, values=self.ComboDetialPlaySourceList, font=('宋体',9))
        self.ComboDetialPlaySource.place(relx=0.187, rely=0.078, relwidth=0.171, relheight=0.024)
        self.ComboDetialPlaySource.set(self.ComboDetialPlaySourceList[0])

        self.style.configure('LabelDetialDownloadType.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialDownloadType = Label(self.FrameDetial, text='选择下载清晰度：', style='LabelDetialDownloadType.TLabel')
        self.LabelDetialDownloadType.place(relx=0.018, rely=0.145, relwidth=0.144, relheight=0.04)

        self.style.configure('LabelDetialDrictor.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialDrictor = Label(self.FrameDetial, text='导演：解析后显示', style='LabelDetialDrictor.TLabel')
        self.LabelDetialDrictor.place(relx=0.544, rely=0.039, relwidth=0.171, relheight=0.03)

        self.style.configure('LabelDetialZone.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialZone = Label(self.FrameDetial, text='地区：解析后显示', style='LabelDetialZone.TLabel')
        self.LabelDetialZone.place(relx=0.366, rely=0.039, relwidth=0.171, relheight=0.03)

        self.style.configure('LabelDetialSort.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialSort = Label(self.FrameDetial, text='分类：解析后显示', style='LabelDetialSort.TLabel')
        self.LabelDetialSort.place(relx=0.187, rely=0.039, relwidth=0.171, relheight=0.03)

        self.style.configure('LabelDetialPlaylist.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialPlaylist = Label(self.FrameDetial, text='播放地址：', style='LabelDetialPlaylist.TLabel')
        self.LabelDetialPlaylist.place(relx=0.018, rely=0.087, relwidth=0.144, relheight=0.04)

        self.style.configure('LabelDetialIntro.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialIntro = Label(self.FrameDetial, text='简介：解析后显示', style='LabelDetialIntro.TLabel')
        self.LabelDetialIntro.place(relx=0.731, rely=0.572, relwidth=0.188, relheight=0.185)

        self.style.configure('LabelDetialRatings.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialRatings = Label(self.FrameDetial, text='评分：解析后显示', style='LabelDetialRatings.TLabel')
        self.LabelDetialRatings.place(relx=0.731, rely=0.504, relwidth=0.188, relheight=0.05)

        self.style.configure('LabelDetialUpdateTime.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialUpdateTime = Label(self.FrameDetial, text='更新时间：解析后显示', style='LabelDetialUpdateTime.TLabel')
        self.LabelDetialUpdateTime.place(relx=0.731, rely=0.436, relwidth=0.197, relheight=0.04)

        self.style.configure('LabelDetialIntroduction.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialIntroduction = Label(self.FrameDetial, text='剧情介绍：解析后显示', style='LabelDetialIntroduction.TLabel')
        self.LabelDetialIntroduction.place(relx=0.071, rely=0.795, relwidth=0.893, relheight=0.137)

        self.style.configure('LabelDetialName.TLabel',anchor='w', font=('宋体',9))
        self.LabelDetialName = Label(self.FrameDetial, text='名称：解析后显示', style='LabelDetialName.TLabel')
        self.LabelDetialName.place(relx=0.018, rely=0.039, relwidth=0.162, relheight=0.03)

        self.style.configure('CommandCheckDetial.TButton',font=('宋体',9))
        self.CommandCheckDetial = Button(self.FrameSearchResault, text='查看详情', command=self.CommandCheckDetial_Cmd, style='CommandCheckDetial.TButton')
        self.CommandCheckDetial.place(relx=0.617, rely=0.881, relwidth=0.291, relheight=0.044)

        self.PictureDetialBox = Canvas(self.FrameSearchResault, bg='#B4B4B4')
        self.PictureDetialBox.place(relx=0.039, rely=0.43, relwidth=0.343, relheight=0.42)

        self.ListResalutVar = StringVar(value='')
        self.ListResalutFont = Font(font=('宋体',9))
        self.ListResalut = Listbox(self.FrameSearchResault, bg='#C0C0C0', listvariable=self.ListResalutVar, font=self.ListResalutFont)
        self.ListResalut.place(relx=0.039, rely=0.086, relwidth=0.908, relheight=0.295)

        self.style.configure('LabelResaultDirector.TLabel',anchor='w', font=('宋体',9))
        self.LabelResaultDirector = Label(self.FrameSearchResault, text='导演：解析后显示', style='LabelResaultDirector.TLabel')
        self.LabelResaultDirector.place(relx=0.407, rely=0.451, relwidth=0.488, relheight=0.034)

        self.style.configure('LabelResaultStar.TLabel',anchor='w', font=('宋体',9))
        self.LabelResaultStar = Label(self.FrameSearchResault, text='主演：解析后显示', style='LabelResaultStar.TLabel')
        self.LabelResaultStar.place(relx=0.407, rely=0.505, relwidth=0.488, relheight=0.119)

        self.style.configure('LabelResaultIntro.TLabel',anchor='w', font=('宋体',9))
        self.LabelResaultIntro = Label(self.FrameSearchResault, text='简介：解析后显示', style='LabelResaultIntro.TLabel')
        self.LabelResaultIntro.place(relx=0.407, rely=0.644, relwidth=0.488, relheight=0.184)

        self.style.configure('LabelResaultEpisode.TLabel',anchor='w', font=('宋体',9))
        self.LabelResaultEpisode = Label(self.FrameSearchResault, text='集数：解析后显示', style='LabelResaultEpisode.TLabel')
        self.LabelResaultEpisode.place(relx=0.053, rely=0.87, relwidth=0.291, relheight=0.055)

        self.style.configure('LabelResaultList.TLabel',anchor='w', font=('宋体',9))
        self.LabelResaultList = Label(self.FrameSearchResault, text='结果列表：', style='LabelResaultList.TLabel')
        self.LabelResaultList.place(relx=0.026, rely=0.032, relwidth=0.12, relheight=0.023)

        self.style.configure('CommandSearch.TButton',font=('宋体',9))
        self.CommandSearch = Button(self.FrameSearch, text='搜索', command=self.CommandSearch_Cmd, style='CommandSearch.TButton')
        self.CommandSearch.place(relx=0.736, rely=0.219, relwidth=0.238, relheight=0.562)

        self.TextInputVar = StringVar(value='')
        self.TextInput = Entry(self.FrameSearch, textvariable=self.TextInputVar, font=('宋体',9))
        self.TextInput.place(relx=0.171, rely=0.219, relwidth=0.54, relheight=0.466)

        self.style.configure('LabelKeyword.TLabel',anchor='w', font=('宋体',9))
        self.LabelKeyword = Label(self.FrameSearch, text='关键字：', style='LabelKeyword.TLabel')
        self.LabelKeyword.place(relx=0.026, rely=0.329, relwidth=0.12, relheight=0.342)
        
        self.style.configure('CommandLastPage.TButton',font=('宋体',9))
        self.CommandLastPage = Button(self.FrameSearchResault, text='上一页', command=self.CommandLastPage_Cmd, style='CommandLastPage.TButton')
        self.CommandLastPage.place(relx=0.131, rely=0.021, relwidth=0.133, relheight=0.055)

        self.style.configure('CommandNextpage.TButton',font=('宋体',9))
        self.CommandNextpage = Button(self.FrameSearchResault, text='下一页', command=self.CommandNextpage_Cmd, style='CommandNextpage.TButton')
        self.CommandNextpage.place(relx=0.276, rely=0.021, relwidth=0.133, relheight=0.055)

        
        # 绑定双击事件
        self.ListResalut.bind('<Double-1>', self.listResalutBoxDoubleClick)
        
        # Bind the select event
        self.ListResalut.bind('<<ListboxSelect>>', self.updateSelectedListResalut)


class Application(Application_ui):
    #这个类实现具体的事件处理回调函数。界面生成代码在Application_ui中。
    def __init__(self, master=None):
        Application_ui.__init__(self, master)
        self.driverInited=False
        initDriver_thread = threading.Thread(target=self.initDriver)
        print("Start to init driver")
        initDriver_thread.start()
        self.CommandSearch['state'] = 'disable'
        self.CommandSearch['text'] = "初始化引擎中..."
        
        
    def initDriver(self):
        print("Loading Chrome.")
        global driver,chrome_options
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
        print("Loading driver")
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)  # 设置隐式等待时间为10秒
        self.driverInited=True
        print("Init driver sucess")
        self.CommandSearch['state'] = 'normal'
        self.CommandSearch['text'] = "搜一搜..."

    def CommandCopyListMag_Cmd(self, event=None):
        #TODO, Please finish the function here!
        pass

    def CommandDownloadAllList_Cmd(self, event=None):
        #TODO, Please finish the function here!
        pass

    def CommandDownloadSelected_Cmd(self, event=None):
        #TODO, Please finish the function here!
        pass

    def CommandDetialOpenEpisodes_Cmd(self, event=None):
        #TODO, Please finish the function here!
        pass

    def CommandDetialDownloadAllEpisodes_Cmd(self, event=None):
        #TODO, Please finish the function here!
        pass

    def CommandDetialDownloadCurrentEpisodes_Cmd(self, event=None):
        #TODO, Please finish the function here!
  
        pass

    def CommandCheckDetial_Cmd(self, event=None):
        #TODO, Please finish the function here!
        title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page,next_page=searchResults[currentIndex]
        detial_thread = threading.Thread(target=self.checkDetial,args=(full_href,))
        detial_thread.start()
        pass

    def CommandSearch_Cmd(self, event=None):
        #TODO, Please finish the function here!
        previous_page_link=""
        next_page_link=""
        self.CommandSearch['state'] = 'disable'
        self.CommandSearch['text'] = "搜索中..."
        self.CommandLastPage['state'] = 'disable'
        self.CommandNextpage['state'] = 'disable'
        txt=self.TextInputVar.get()
        if txt=="":
            self.CommandLastPage['state'] = 'normal'
            self.CommandNextpage['state'] = 'normal'
            self.CommandSearch['state'] = 'normal'
            self.CommandSearch['text'] = "搜一下"
            return
        # 打开目标网页https://m.meijume.com/search.php?searchword=%E5%90%B8%E8%A1%80%E9%AC%BC&submit=
        url="https://m.meijume.com/search.php?searchword="+txt
        search_thread = threading.Thread(target=self.doSearch,args=(url,))
        search_thread.start()
        pass


    def CommandLastPage_Cmd(self, event=None):
        #TODO, Please finish the function here!
        print("解析上一页：",previous_page_link)
        self.CommandSearch['state'] = 'disable'
        self.CommandSearch['text'] = "搜索中..."
        self.CommandLastPage['state'] = 'disable'
        self.CommandNextpage['state'] = 'disable'
        if previous_page_link=="":
            self.CommandLastPage['state'] = 'normal'
            self.CommandNextpage['state'] = 'normal'
            self.CommandSearch['state'] = 'normal'
            self.CommandSearch['text'] = "搜一下"
            return
        search_thread = threading.Thread(target=self.doSearch,args=(previous_page_link,))
        search_thread.start()
        pass

    def CommandNextpage_Cmd(self, event=None):
       #TODO, Please finish the function here!
        print("解析下一页：",next_page_link)
        self.CommandSearch['state'] = 'disable'
        self.CommandSearch['text'] = "搜索中..."
        self.CommandLastPage['state'] = 'disable'
        self.CommandNextpage['state'] = 'disable'
        if next_page_link=="":
            self.CommandLastPage['state'] = 'normal'
            self.CommandNextpage['state'] = 'normal'
            self.CommandSearch['state'] = 'normal'
            self.CommandSearch['text'] = "搜一下"
            return
        search_thread = threading.Thread(target=self.doSearch,args=(next_page_link,))
        search_thread.start()
        pass

    def listResalutBoxDoubleClick(self, event):
        #TODO, Please finish the function here!
        global currentIndex
        index = self.ListResalut.curselection()
        if index:
            index = index[0]  # 获取第一个（也是唯一一个）选中项的索引
            title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page,next_page=searchResults[index]
            # print(f"你双击了: {title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page,next_page}")
            # 在这里添加你想要执行的操作
            currentIndex=index
            self.LabelResaultDirector.config(text=p_dy)
            self.LabelResaultStar.config(text=p_zy)
            self.LabelResaultEpisode.config(text=p_fl)
            self.LabelResaultIntro.config(text=p_jj)
            self.display_image(full_data_original)
        pass


    def updateSelectedListResalut(self, event):
        global currentIndex
        # Get the index of the selected item
        widget = event.widget
        index = int(widget.curselection()[0])
        value = widget.get(index)
        # Output the index and the value of the selected item
        # print(f'Selected Item Index: {index}, Value: {value}')
        if index:
            currentIndex=index
            title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page,next_page=searchResults[currentIndex]
            self.LabelResaultDirector.config(text=p_dy)
            self.LabelResaultStar.config(text=p_zy)
            self.LabelResaultEpisode.config(text=p_fl)
            self.LabelResaultIntro.config(text=p_jj)
            self.display_image(full_data_original)
        pass


    def updateListResalut(self,datas):
        # 清空Listbox中的所有项
        self.ListResalut.delete(0, 'end')
        for title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page_link,next_page_link in datas:
            # print(f"Title: {title_text}, Href: {full_href}")
            self.ListResalut.insert('end', title_text)
    
    def checkDetial(self,url):
        global mainUrl,juji
        self.CommandCheckDetial['state'] = 'disable'
        self.CommandCheckDetial['text'] = "详情加载中..."
        # 打开目标网页
        print("Opening url:[%s]"%url)
        driver.get(url)  # 替换为你的目标网址
        
        logs = driver.get_log('performance')
             
        while not page_has_loaded(driver):
            # 等待页面加载完成
            time.sleep(1)  # 根据需要调整等待时间
            pass
        self.CommandCheckDetial['state'] = 'normal'
        self.CommandCheckDetial['text'] = "点击查看详情"
        print("Loaded url:[%s]"%url)
        
        pagesource=driver.page_source
        
        pianYuanList=get_play_list_pianyuan_and_playlistid(pagesource)
        pianYuanTextList=[]
        juji={}
        for pianyuan,pianyuanid in pianYuanList:
            juji[str(pianyuan).strip()]={}
            juji[str(pianyuan).strip()]["ids"]=[]
            juji[str(pianyuan).strip()]["ids"].append(pianyuanid)
            
            pianYuanTextList.append(str(pianyuan))
            
            jujipianyuanidList=get_play_list_juji_text_and_link(pagesource,pianyuanid,mainUrl)
            jujipianyuanidTextList=[]
            jujipianyuanidLinkList=[]
            for jujiText,jujiLink in jujipianyuanidList:
                jujipianyuanidTextList.append(str(jujiText))
                jujipianyuanidLinkList.append(str(jujiLink))
                juji[str(pianyuan).strip()][str(jujiText)]=jujiLink
            juji[str(pianyuan).strip()]['texts']=jujipianyuanidTextList
            juji[str(pianyuan).strip()]['links']=jujipianyuanidLinkList
        print("在线片源：",pianYuanTextList)
                
        qingXiDuTextList=[]
        exclude_texts = ["播放地址", "猜你喜欢", "正在热播", "热播电影频道", "最新资讯", "剧情介绍","热播综艺频道","热播","热播剧集频道"]
        for qxdtext in get_filtered_h3_text(pagesource,exclude_texts):
            qingXiDuTextList.append(qxdtext)
            # qxdtextkey=str(qxdtext)
            downloadsinfo=get_download_list_text_and_link(pagesource,qxdtext)
            for text, href in downloadsinfo:
                juji[str(qxdtext).strip()][str(text).strip()]=href
                print(f'Download:   Text: {text}, Href: {href}')
        print("清晰度：",qingXiDuTextList)
        juji['sources']=qingXiDuTextList
        
        print("======================")
        print(juji)
        print("======================")
        
        for entry in logs:
            message = json.loads(entry["message"])
            message = message["message"]
            if message["method"] == "Network.requestWillBeSent":
                murl = message["params"]["request"]["url"]
                urls.add(murl)
        # 先检查是否存在 .m3u8 链接
        h1_text=get_h1_text(pagesource)
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(pagesource, 'html.parser')
        # 定位到ID为'desc'的div
        desc_div = soup.find('div', id='desc')
        # 在找到的div内部，进一步定位到class为'sketch content'的span标签
        sketch_content_span = desc_div.find('span', class_='sketch content')
        # 获取span标签的文本内容
        if sketch_content_span:
            mtext = sketch_content_span.get_text(strip=True)
            # print(mtext)
        else:
            mtext=""
            print("Element not found")
        title = h1_text
        self.LabelDetialIntroduction.config(text=mtext)
        self.LabelDetialName.config(text=title)
        # print("Title of the page:", title)

    def doSearch(self,pageurl):
        global searchResults,currentIndex,currentImages
        searchResults = []
        currentIndex=0
        currentImages={}       
        print("Opening url:[%s]"%pageurl)
        driver.get(pageurl)  # 替换为你的目标网址
        print("Loaded url:[%s]"%pageurl)
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
        datas=readSearchResaultData(driver.page_source)          
        self.updateListResalut(datas)
        #TODO, Please finish the function here!
        self.CommandSearch['state'] = 'normal'
        self.CommandSearch['text'] = "搜一下"
        self.CommandLastPage['state'] = 'normal'
        self.CommandNextpage['state'] = 'normal'

    def display_image(self,image_url):
        if image_url in currentImages.keys():
            image=currentImages[image_url]
        else:
            response = requests.get(image_url)
            image_data = BytesIO(response.content)
            image = Image.open(image_data)
            currentImages[image_url]=image

        # 计算缩放比例，使宽度适应205像素
        scale = 205 / image.width
        new_height = int(image.height * scale)
        
        # 缩放图像
        image = image.resize((205, new_height), Image.Resampling.LANCZOS)

        self.photo_image = ImageTk.PhotoImage(image)
        
        # 如果新的高度小于309，则计算垂直居中的位置
        y_position = (309 - new_height) // 2 if new_height < 309 else 0

        # 显示图像，并确保它在垂直方向上居中（如果需要）
        self.PictureDetialBox.create_image(0, y_position, anchor="nw", image=self.photo_image)
 

def loadImage(image_url):
    response = requests.get(image_url)
    image_data = BytesIO(response.content)
    image = Image.open(image_data)
    currentImages[image_url]=image
    pass


def readSearchResaultData(page_source):
    global currentImages,previous_page_link,next_page_link,currentIndex,searchResults
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')

    # 查找所有class为myui-vodlist__media clearfix的ul标签
    ul_tags = soup.find_all('ul', class_='myui-vodlist__media clearfix')
    
    # 定位到class为'myui-page text-center clearfix'的ul标签
    pagination_ul = soup.find('ul', class_='myui-page')
    # 初始化结果字典
    results = {
        "btn_warm_text": None,
        "previous_page_link": None,
        "next_page_link": None
    }
    # 查找class为'btn btn-warm'的a标签
    btn_warm_a = pagination_ul.find('a', class_='btn btn-warm')
    if btn_warm_a:
        results['btn_warm_text'] = btn_warm_a.text.strip()
    # 查找text为“上一页”的a标签
    previous_page_a = pagination_ul.find('a', text="上一页")
    if previous_page_a:
        previou=previous_page_a['href']
        results['previous_page_link'] = f'https://m.meijume.com/search.php{previou}' 
        previous_page_link=results['previous_page_link'].strip()
        print("上一页:",previous_page_link)
    # 查找text为“下一页”的a标签
    next_page_a = pagination_ul.find('a', text="下一页")
    if next_page_a:
        nextl=next_page_a['href']
        results['next_page_link'] = f'https://m.meijume.com/search.php{nextl}' 
        next_page_link=results['next_page_link'].strip()
        print("下一页:",next_page_link)
    # print(results)   
    
    p_dy=""
    p_zy=""
    p_fl=""
    p_dq=""
    p_nf=""
    p_jj=""
    
    for ul in ul_tags:
        li_tags = ul.find_all('li')
        for li in li_tags:
            # 获取h4标签的文本和a标签的href属性
            h4_tag = li.find('h4', class_='title')
            if h4_tag:
                title_text = h4_tag.get_text(strip=True)
                a_tag = h4_tag.find('a')
                if a_tag and a_tag.has_attr('href'):
                    href = a_tag['href']
                    full_href = f'https://m.meijume.com/{href}'

            # 获取指定开头的p标签文本
            p_tags = li.find_all('p')
            for p in p_tags:
                if p.text.startswith(('导演：', '主演：', '分类：', '地区：', '年份：', '简介：')):
                    # print(p.text)
                    if p.text.startswith('导演：'):
                        p_dy=str(p.text).strip()
                    if p.text.startswith('主演：'):
                        p_zy=p.text
                    if p.text.startswith('分类：'):
                        p_fl=p.text
                    if p.text.startswith('地区：'):
                        p_dq=p.text
                    if p.text.startswith('年份：'):
                        p_nf=p.text
                    if p.text.startswith('简介：'):
                        p_jj=p.text
               
            # 获取class为myui-vodlist__thumb的a标签的data-original属性
            a_thumb_tag = li.find('a', class_='myui-vodlist__thumb')
            if a_thumb_tag and a_thumb_tag.has_attr('data-original'):
                data_original = a_thumb_tag['data-original']
                full_data_original = f'https://m.meijume.com/{data_original}'
                full_data_original=full_data_original.replace("//img.php?url=","")
                loadImage_thread = threading.Thread(target=loadImage,args=(full_data_original,))
                loadImage_thread.start()
            searchResults.append((title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj,previous_page_link,next_page_link))
            # 根据需要输出或处理获取到的信息
            # print(title_text, full_href, full_data_original,p_dy,p_zy,p_fl,p_dq,p_nf,p_jj)
    
    return searchResults


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



def get_h3_text(page_source):
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(page_source, 'html.parser')
    # 使用 find_all 方法查找所有 h3 标签，然后过滤掉包含指定文本的标签
    filtered_texts = [h3_tags.text for h3_tags in soup.find_all('h3')]
    return filtered_texts

def get_filtered_h3_text(page_source,exclude_texts):
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(page_source, 'html.parser')
    # 使用 find_all 方法查找所有 h3 标签，然后过滤掉包含指定文本的标签
    filtered_texts = [h3_tags.text for h3_tags in soup.find_all('h3') if not any(exclude_text in h3_tags.text for exclude_text in exclude_texts)]
    return filtered_texts
  
def get_panel_source_by_h3_text(page_source,h3_text):
    # myui-panel myui-panel-bg clearfix
    # 获取页面源代码
    html_source =page_source
    # 使用BeautifulSoup解析HTML
    soup = BeautifulSoup(html_source, 'html.parser')
    # 查找所有 class 为 myui-panel myui-panel-bg clearfix 的 div
    divs = soup.find_all('div', class_='myui-panel myui-panel-bg clearfix')
    # 遍历这些 div，寻找包含有文字 'abc' 的 h3
    for div in divs:
        h3 = div.find('h3',  string=lambda text: h3_text in text)
        ul=div.find('ul')
        if ul:
            if h3:
                return div
    pass


def get_play_list_pianyuan_and_playlistid(page_source):
    # 查找所有文本为“播放地址”的 h3 标签
    # 使用 BeautifulSoup 解析 HTML
    playlistDiv = get_panel_source_by_h3_text(page_source,"播放地址")
    playlist_ul=None
    playlist_ul = playlistDiv.find('ul')
    if not playlist_ul:
        return None
    # 结果列表，用于存储匹配的 a 标签的文本和 href
    results = []
    if playlist_ul:
        # 遍历 ul 内的所有 li 元素
        for li in playlist_ul.find_all('li'):
            # 在每个 li 内找到所有 a 标签
            for a in li.find_all('a'):
                # 检查 a 标签的 href 是否以 # 开头
                if a.get('href', '').startswith('#'):
                    # 提取 href 属性的值以及去除 # 后的文本值
                    href_value = a['href']
                    text_value = a.text
                    results.append((text_value.replace('#', ''), href_value))
    # 打印结果
    for text, href in results:
        print(f'get_play_list_pianyuan_and_playlistid   Text: {text}, Href: {href}')
    return results
 

def get_play_list_juji_text_and_link(page_source,pianyuanid,mainurl):
    playlist_div=get_panel_source_by_h3_text(page_source,"播放地址")
    # print(pianyuanid)
    pianyuanidtext=str(pianyuanid).removeprefix("#")
    pianyuan=playlist_div.find(id=pianyuanidtext)
    # 查找所有 class 为 myui-content__list 的 ul
    ul = pianyuan.find('ul', class_='myui-content__list')
    # 结果列表，用于存储每个 a 标签的文本和补齐的 href
    results = []
    if ul:
        # 遍历 ul 下的所有 li 元素
        for li in ul.find_all('li'):
            # 在每个 li 内找到 a 标签
            a_tag = li.find('a')
            if a_tag:
                # 获取 a 标签的文本和 href 属性
                text = a_tag.text
                href = a_tag['href']
                # 如果 href 不以 mainurl 开头，则补齐
                if not href.startswith(mainurl):
                    href = mainurl + href
                results.append((text, href))
    # 打印结果
    for text, href in results:
        print(f'get_play_list_juji_text_and_link    Text: {text}, Href: {href}')
    return results

def get_download_list_text_and_link(page_source,qingxidutext):
    download_div=get_panel_source_by_h3_text(page_source,qingxidutext)
    # 结果列表，用于存储每个匹配项的信息
    results = []
    # 查找ul元素，这里假设只有一个ul，如果有多个，可能需要更精确的定位
    ul = download_div.find('ul')
    # 遍历ul下所有class为bottom-line clearfix的li元素
    for li in ul.find_all('li', class_='bottom-line clearfix'):
        # 获取li下class为text的span下的a标签的文本
        text_a = li.find('span', class_='text').find('a')
        text = text_a.text if text_a else 'N/A'
        
        # 获取li下class为operate的span下class为btn bendi的a标签的href
        operate_a = li.find('span', class_='operate').find('a', class_='btn bendi')
        href = operate_a['href'] if operate_a else 'N/A'
        
        # 添加到结果列表
        results.append((text, href))

    # 打印结果
    for text, href in results:
        print(f'get_download_list_text_and_link   Text: {text}, Href: {href}')
    return results

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

 


if __name__ == "__main__":
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
    # 初始化一个列表来保存结果
    searchResults = []
    currentIndex=0
    currentImages={}
    previous_page_link=""
    next_page_link=""
    mainUrl="https://m.meijume.com/"
    juji={}
    driver=None
     
    

    top = Tk()
    Application(top).mainloop()
    try:
        top.destroy()
        # 关闭浏览器
        driver.quit()
        print("Driver exit.")
    except: pass
    
