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
    import tkFileDialog
    #import tkSimpleDialog
else:  #Python 3.x
    PythonVersion = 3
    from tkinter.font import Font
    from tkinter.ttk import *
    from tkinter.messagebox import *
    import tkinter.filedialog as tkFileDialog
    #import tkinter.simpledialog as tkSimpleDialog    #askstring()

class Application_ui(Frame):
    #这个类仅实现界面生成功能，具体事件处理代码在子类Application中。
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master.title('Yatu视频下载')
        self.master.geometry('1200x700')
        self.createWidgets()

    
    def createWidgets(self):
        self.top = self.winfo_toplevel()

        self.style = Style()

        self.style.configure('ChromeFrame.TLabelframe',font=('宋体',9))
        self.ChromeFrame = LabelFrame(self.top, text='浏览器下载', style='ChromeFrame.TLabelframe')
        self.ChromeFrame.place(relx=0.007, rely=0.511, relwidth=0.983, relheight=0.478)

        self.style.configure('VideoDownloaderFrame.TLabelframe',font=('宋体',9))
        self.VideoDownloaderFrame = LabelFrame(self.top, text='视频下载', style='VideoDownloaderFrame.TLabelframe')
        self.VideoDownloaderFrame.place(relx=0.007, rely=0.012, relwidth=0.983, relheight=0.489)

        self.style.configure('CloseChromeBtn.TButton',font=('宋体',9))
        self.CloseChromeBtn = Button(self.ChromeFrame, text='关闭浏览器', command=self.CloseChromeBtn_Cmd, style='CloseChromeBtn.TButton')
        self.CloseChromeBtn.place(relx=0.028, rely=0.535, relwidth=0.106, relheight=0.149)

        self.LogListVar = StringVar(value='')
        self.LogListFont = Font(font=('宋体',9))
        self.LogList = Listbox(self.ChromeFrame, listvariable=self.LogListVar, font=self.LogListFont)
        self.LogList.place(relx=0.162, rely=0.097, relwidth=0.803, relheight=0.851)

        self.style.configure('AlyseBtn.TButton',font=('宋体',9))
        self.AlyseBtn = Button(self.ChromeFrame, text='分析当前页面', command=self.AlyseBtn_Cmd, style='AlyseBtn.TButton')
        self.AlyseBtn.place(relx=0.028, rely=0.316, relwidth=0.106, relheight=0.149)

        self.style.configure('OpenChromeBtn.TButton',font=('宋体',9))
        self.OpenChromeBtn = Button(self.ChromeFrame, text='打开浏览器', command=self.OpenChromeBtn_Cmd, style='OpenChromeBtn.TButton')
        self.OpenChromeBtn.place(relx=0.028, rely=0.097, relwidth=0.106, relheight=0.149)

        self.style.configure('StopDownloadBtn.TButton',font=('宋体',9))
        self.StopDownloadBtn = Button(self.VideoDownloaderFrame, text='停止下载', command=self.StopDownloadBtn_Cmd, style='StopDownloadBtn.TButton')
        self.StopDownloadBtn.place(relx=0.894, rely=0.665, relwidth=0.092, relheight=0.122)

        self.style.configure('DownloadListBtn.TButton',font=('宋体',9))
        self.DownloadListBtn = Button(self.VideoDownloaderFrame, text='下载队列', command=self.DownloadListBtn_Cmd, style='DownloadListBtn.TButton')
        self.DownloadListBtn.place(relx=0.894, rely=0.522, relwidth=0.092, relheight=0.122)

        self.style.configure('AddListBtn.TButton',font=('宋体',9))
        self.AddListBtn = Button(self.VideoDownloaderFrame, text='添加到队列', command=self.AddListBtn_Cmd, style='AddListBtn.TButton')
        self.AddListBtn.place(relx=0.894, rely=0.38, relwidth=0.092, relheight=0.122)

        self.DownloadListVar = StringVar(value='')
        self.DownloadListFont = Font(font=('宋体',9))
        self.DownloadList = Listbox(self.VideoDownloaderFrame, listvariable=self.DownloadListVar, font=self.DownloadListFont)
        self.DownloadList.place(relx=0.091, rely=0.38, relwidth=0.789, relheight=0.546)

        self.style.configure('ChoseFolderBtn.TButton',font=('宋体',9))
        self.ChoseFolderBtn = Button(self.VideoDownloaderFrame, text='选择下载目录', command=self.ChoseFolderBtn_Cmd, style='ChoseFolderBtn.TButton')
        self.ChoseFolderBtn.place(relx=0.894, rely=0.19, relwidth=0.092, relheight=0.122)

        self.style.configure('DownloadBtn.TButton',font=('宋体',9))
        self.DownloadBtn = Button(self.VideoDownloaderFrame, text='下载视频', command=self.DownloadBtn_Cmd, style='DownloadBtn.TButton')
        self.DownloadBtn.place(relx=0.894, rely=0.047, relwidth=0.092, relheight=0.122)

        self.M3U8AdressTextVar = StringVar(value='')
        self.M3U8AdressText = Entry(self.VideoDownloaderFrame, textvariable=self.M3U8AdressTextVar, font=('宋体',9))
        self.M3U8AdressText.place(relx=0.091, rely=0.071, relwidth=0.5, relheight=0.098)

        self.style.configure('Label3.TLabel',anchor='w', font=('宋体',9))
        self.Label3 = Label(self.VideoDownloaderFrame, text='下载队列：', style='Label3.TLabel')
        self.Label3.place(relx=0.014, rely=0.38, relwidth=0.057, relheight=0.074)

        self.DownloadFolderLabelVar = StringVar(value='')
        self.style.configure('DownloadFolderLabel.TLabel',anchor='w', font=('宋体',9))
        self.DownloadFolderLabel = Label(self.VideoDownloaderFrame,  textvariable=self.DownloadFolderLabelVar, style='DownloadFolderLabel.TLabel')
        self.DownloadFolderLabel.place(relx=0.091, rely=0.237, relwidth=0.782, relheight=0.074)
 
        self.style.configure('Label2.TLabel',anchor='w', font=('宋体',9))
        self.Label2 = Label(self.VideoDownloaderFrame, text='下载目录：', style='Label2.TLabel')
        self.Label2.place(relx=0.014, rely=0.237, relwidth=0.057, relheight=0.074)

        self.style.configure('Label1.TLabel',anchor='w', font=('宋体',9))
        self.Label1 = Label(self.VideoDownloaderFrame, text='M3U8地址：', style='Label1.TLabel')
        self.Label1.place(relx=0.014, rely=0.095, relwidth=0.057, relheight=0.05)

        self.FilenameTextVar = StringVar(value='')
        self.FilenameText = Entry(self.VideoDownloaderFrame, textvariable=self.FilenameTextVar, font=('宋体',9))
        self.FilenameText.place(relx=0.704, rely=0.071, relwidth=0.177, relheight=0.098)

        self.style.configure('Label4.TLabel',anchor='w', font=('宋体',9))
        self.Label4 = Label(self.VideoDownloaderFrame, text='文件名：', style='Label4.TLabel')
        self.Label4.place(relx=0.64, rely=0.095, relwidth=0.05, relheight=0.05)




class Application(Application_ui):
    #这个类实现具体的事件处理回调函数。界面生成代码在Application_ui中。
    def __init__(self, master=None):
        Application_ui.__init__(self, master)
        self.DownloadListBtn.config(state="disable")
        self.DownloadBtn.config(state="disable")
        self.path=os.path.dirname(os.path.realpath(sys.argv[0]))
        self.downloadUrl=""
        self.downloadFoderPath=""
        self.downloadUrlList={}
        self.logs=[]
        self.driver =None
        self.LogList.insert(0,"LOG:")
        self.downloading=False
        path=os.path.dirname(os.path.realpath(sys.argv[0]))
        tmpDir=path+"\\Downloads\\"
        if not os.path.exists(tmpDir):
            print("tmp missing creat...")
            os.makedirs(tmpDir) 
            print("tmp missing created!")
            print("tmp inited!")
        self.downloadFoderPath=tmpDir
        self.DownloadFolderLabelVar.set(tmpDir)
        self.AddLog("Check Bin Files",4)
        downloadBinProcess = threading.Thread(target=self.downloadBin)
        downloadBinProcess.start()
        loadWebServerProcess = threading.Thread(target=loadServer)
        loadWebServerProcess.start()
        print("System Ready!")
        

    def CloseChromeBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!\
        print("CloseChromeBtn_Cmd")
        pass

    def AlyseBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        print("AlyseBtn_Cmd")
        alysProcess = threading.Thread(target=self.alysChromePage)
        alysProcess.start()
        pass

    def alysChromePage(self, event=None):
        print("alysChromePage")
        time.sleep(5)
        print("alysChromePage Finished")
        pass

    def OpenChromeBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        print("OpenChromeBtn_Cmd")
        pass

    def ChoseFolderBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.AddLog("ChoseFolderBtn_Cmd",10)
        folder_selected = tkFileDialog.askdirectory()
        self.AddLog("Folder:[%s]"%folder_selected,10)
        self.downloadFoderPath=folder_selected
        self.DownloadFolderLabelVar.set(folder_selected)
        pass

    def DownloadBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.AddLog("DownloadBtn_Cmd",8)
        self.DownloadListBtn.config(state="disable")
        if self.downloading:
            self.AddLog("System Downloading...Pls wait Finish",4)
            # return
        self.downloadUrl=self.M3U8AdressTextVar.get()
        if self.downloadUrl.lower().startswith("http")  :
            self.AddLog("address:[%s]"%self.downloadUrl,4)
            if len(self.FilenameText.get())>0:
                filenameStr=self.FilenameText.get().replace('*','').replace('\\','').replace('#','').replace('@','').replace('$','')
            # downLoadM3U8(self.downloadUrl,filenameStr)
            downloadProcess = threading.Thread(target=self.downLoadM3U8,args=(self.downloadUrl,filenameStr))
            self.downloading=True
            downloadProcess.start()

        else:
            self.AddLog("address:[%s] ERR"%self.downloadUrl,8)
        if  not self.downloading:
            self.DownloadListBtn.config(state="NORMAL")
            self.DownloadBtn.config(state="NORMAL")
        pass

    def getFileName(self):
        if len(self.FilenameText.get())>0:
                return self.FilenameText.get().replace('*','').replace('\\','').replace('#','').replace('@','').replace('$','').replace(':','').replace('>','').replace('<','').replace('=','')
        return str(time.time()).replace('*','').replace('\\','').replace('#','').replace('@','').replace('$','').replace(':','').replace('>','').replace('<','').replace('=','')

    def AddListBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.AddLog("AddListBtn_Cmd",6)
        if self.M3U8AdressTextVar.get().lower().startswith("http") :
            # and self.M3U8AdressTextVar.get().lower().endswith("m3u8")
            self.AddLog("address:[%s]"%self.M3U8AdressTextVar.get(),2)
            if self.M3U8AdressTextVar.get() not in self.downloadUrlList.values():
                self.downloadUrlList[self.getFileName()]=(self.M3U8AdressTextVar.get())
                self.DownloadList.insert(0,self.M3U8AdressTextVar.get())
                self.AddLog("address add:[%s]"%self.M3U8AdressTextVar.get(),4)
            else:
                for keyw in  self.downloadUrlList.keys():
                    if self.downloadUrlList[keyw]==self.M3U8AdressTextVar.get():
                        if self.getFileName()==keyw:
                            self.AddLog("address added:[%s]"%self.M3U8AdressTextVar.get(),6)
                            break
                        else:
                            try:
                                self.downloadUrlList.pop(keyw)
                                self.downloadUrlList[self.getFileName()]=self.M3U8AdressTextVar.get()
                                self.AddLog("address added:[%s] and Updated Filename:[%s]"%(self.M3U8AdressTextVar.get(),self.getFileName()),6)
                                break
                            except Exception as e:
                                print(e)
        else:
            self.AddLog("address:[%s] ERR"%self.M3U8AdressTextVar.get(),8)
        pass
        pass

    def DownloadListBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.AddLog("DownloadListBtn_Cmd",4)
        downloadListsProcess = threading.Thread(target=self.downloadLists)
        downloadListsProcess.start()
    

    def downloadLists(self):
        self.downloading=False
        for keyv in    self.downloadUrlList.keys():
            while self.downloading:
                time.sleep(3)
            downloadProcess = threading.Thread(target=self.downLoadM3U8,args=(self.downloadUrlList[keyv],keyv))
            self.downloading=True
            self.DownloadListBtn.config(state="disable")
            self.DownloadBtn.config(state="disable")
            downloadProcess.start()
        while self.downloading:
            time.sleep(3)
        if  not self.downloading:
            self.DownloadListBtn.config(state="NORMAL")
            self.DownloadBtn.config(state="NORMAL")
        pass


    def StopDownloadBtn_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.AddLog("StopDownloadBtn_Cmd",2)
        pass

    def AddLog(self,logstr):
        self.AddLog(logstr,0)

    def AddLog(self,logstr,loglevel):
        print("LOG:[%s]"%logstr)
        self.LogList.insert(1,logstr)
        if loglevel:
            if loglevel>1:
                self.LogList.itemconfig(1,bg="#A8ABC4")  
                self.LogList.itemconfig(1,fg="#000000")
            if loglevel>3:
                self.LogList.itemconfig(1,bg="#97EEEC")  #Green
                self.LogList.itemconfig(1,fg="#000000")
            if loglevel>5:
                self.LogList.itemconfig(1,bg="#FFF200")  #Yellow
                self.LogList.itemconfig(1,fg="#000000")
            if loglevel>7:
                self.LogList.itemconfig(1,bg="#FF466F")  #Yan
                self.LogList.itemconfig(1,fg="#000000")
            if loglevel>9:
                self.LogList.itemconfig(1,bg="#D33637")  #Red
                self.LogList.itemconfig(1,fg="#000000")
 

    def downLoadM3U8(self,url,fileName):
        self.DownloadListBtn.config(state="disable")
        self.DownloadBtn.config(state="disable")
        path=os.path.dirname(os.path.realpath(sys.argv[0]))
        programPath=path+"\\Bin\\"
        if not os.path.exists(programPath):
            print("programPath missing creat...")
            os.makedirs(programPath) 
            print("programPath missing created!")
            print("programPath inited!")
        maxThreads=32
        processor=programPath+"\\cli.exe"
        if not os.path.exists(processor):
            print("processor missing...")
            processor=path+"\\cli.exe"
            if not os.path.exists(processor):
                print("root processor missing...")
                self.downloading=False
                return None
        # param = "  -workDir %s -saveName %s  -maxThreads %s -enableDelAfterDone -disableDateInfo  "%(tmpDir,fileName,maxThreads)
        command = [processor, url, "--workDir",self.downloadFoderPath,"--saveName",fileName,"--maxThreads",str(maxThreads),"--enableDelAfterDone","--disableDateInfo"]
        self.AddLog("Download Start: %s [%s]"%(fileName,url),0)
        returnvar=subprocess.run(command)
        self.AddLog("Download Finish: %s [%s]"%(fileName,url),0)
        self.downloading=False
        if  not self.downloading:
            self.DownloadListBtn.config(state="NORMAL")
            self.DownloadBtn.config(state="NORMAL")
        return returnvar


    

    def downloadBin(self):
        try:
            self.downloading=True
            path=os.path.dirname(os.path.realpath(sys.argv[0]))
            programPath=path+"\\Bin\\"
            processor=programPath+"\\cli.exe"
            ffmpegFile=programPath+"\\ffmpeg.exe"
            if not os.path.exists(processor):                
                if not os.path.exists(programPath):
                    print("programPath missing creat...")
                    self.AddLog("programPath missing created...",7)
                    os.makedirs(programPath) 
                self.AddLog("Downloading CLi...",5)
                processorurl='https://github.com/wangzhenjjcn/Yatu_Downloader/releases/download/Pre/cli.exe'
                response = requests.get(processorurl, stream=True)
                response.raise_for_status()  # Raise an exception for HTTP errors
                # Create a temporary directory
                with open(processor, 'wb') as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                self.AddLog("Downloaded CLi cli.exe:[%s]..."%self.compute_md5(processor),9)
                time.sleep(1)
            else:
                self.AddLog("Downloaded CLi cli.exe:[%s]..."%self.compute_md5(processor),5)
            


            if not os.path.exists(ffmpegFile):                
                if not os.path.exists(programPath):
                    print("programPath missing creat...")
                    self.AddLog("programPath missing created...",7)
                    os.makedirs(programPath) 
                self.AddLog("Downloading ffmpeg...",5)
                ffmpegurl='https://github.com/wangzhenjjcn/Yatu_Downloader/releases/download/Pre/ffmpeg.exe'
                response2 = requests.get(ffmpegurl, stream=True)
                response2.raise_for_status()  # Raise an exception for HTTP errors
                # Create a temporary directory
                with open(ffmpegFile, 'wb') as file2:
                    for chunk2 in response2.iter_content(chunk_size=8192):
                        file2.write(chunk2)
                self.AddLog("Downloaded ffmpeg ffmpeg.exe:[%s]..."%self.compute_md5(ffmpegFile),9)
            else:
                self.AddLog("Downloaded ffmpeg ffmpeg.exe:[%s]..."%self.compute_md5(ffmpegFile),5)
            time.sleep(1)
            self.downloading=False
        except Exception as e:
            self.AddLog(str(e),9)
            print(e)
        if self.compute_md5(processor)=="426443628a70ea47ac05b67f665666c1":
            self.AddLog("Check cli.exe:[%s] Success:[426443628a70ea47ac05b67f665666c1]..."%self.compute_md5(ffmpegFile),5)
        else:
            self.AddLog("Check cli err cli.exe:[%s] require:[426443628a70ea47ac05b67f665666c1]..."%self.compute_md5(ffmpegFile),5)
            self.downloading=True
        if  self.compute_md5(ffmpegFile)=="d2375a936c266904c2eb225ce9828047":
            self.AddLog("Check ffmpeg ffmpeg.exe:[%s] Success:[d2375a936c266904c2eb225ce9828047]..."%self.compute_md5(ffmpegFile),5)
        else:
            self.downloading=True
            self.AddLog("Check ffmpeg err ffmpeg.exe:[%s] require:[d2375a936c266904c2eb225ce9828047]..."%self.compute_md5(ffmpegFile),5)
        if  not self.downloading:
            self.DownloadListBtn.config(state="NORMAL")
            self.DownloadBtn.config(state="NORMAL")




    def compute_md5(self,file_path):
        """Compute and return the MD5 hash of a file."""
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        return md5.hexdigest()



webapp = Flask(__name__)
@webapp.route('/')
def hello_world():
    return 'Hello, World!'

@webapp.route('/dl/<name>')
def greet(name):
    return f'Hello, {name}!'

def loadServer():
    webapp.run(host='0.0.0.0', port=8080)

if __name__ == "__main__":
    top = Tk()
    
    Application(top).mainloop()
    try: top.destroy()
    except: pass
