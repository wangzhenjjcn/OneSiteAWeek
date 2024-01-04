#!/usr/bin/env python
#-*- coding:utf-8 -*-

import os, sys
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

class Application_ui(Frame):
    #这个类仅实现界面生成功能，具体事件处理代码在子类Application中。
    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.master.title('MyazureToolBox')
        self.master.geometry('1584x861')
        self.createWidgets()

    def createWidgets(self):
        self.top = self.winfo_toplevel()

        self.style = Style()

        self.style.configure('ControlFrame.TLabelframe',font=('宋体',9))
        self.ControlFrame = LabelFrame(self.top, text='Control', style='ControlFrame.TLabelframe')
        self.ControlFrame.place(relx=0.177, rely=0.502, relwidth=0.794, relheight=0.475)

        self.style.configure('StatusFrame.TLabelframe',font=('宋体',9))
        self.StatusFrame = LabelFrame(self.top, text='Status', style='StatusFrame.TLabelframe')
        self.StatusFrame.place(relx=0.177, rely=0.009, relwidth=0.794, relheight=0.475)

        self.style.configure('ServiceFrame.TLabelframe',font=('宋体',9))
        self.ServiceFrame = LabelFrame(self.top, text='Service', style='ServiceFrame.TLabelframe')
        self.ServiceFrame.place(relx=0.015, rely=0.009, relwidth=0.142, relheight=0.977)

        self.CommandTextVar = StringVar(value='')
        self.CommandText = Entry(self.StatusFrame, textvariable=self.CommandTextVar, font=('宋体',9))
        self.CommandText.place(relx=0.178, rely=0.782, relwidth=0.777, relheight=0.081)

        self.style.configure('StatusCommandFive.TButton',font=('宋体',9))
        self.StatusCommandFive = Button(self.StatusFrame, text='StatusCommand', command=self.StatusCommandFive_Cmd, style='StatusCommandFive.TButton')
        self.StatusCommandFive.place(relx=0.038, rely=0.763, relwidth=0.103, relheight=0.1)

        self.style.configure('StatusCommandFour.TButton',font=('宋体',9))
        self.StatusCommandFour = Button(self.StatusFrame, text='StatusCommand', command=self.StatusCommandFour_Cmd, style='StatusCommandFour.TButton')
        self.StatusCommandFour.place(relx=0.038, rely=0.606, relwidth=0.103, relheight=0.1)

        self.style.configure('StatusCommandThree.TButton',font=('宋体',9))
        self.StatusCommandThree = Button(self.StatusFrame, text='StatusCommand', command=self.StatusCommandThree_Cmd, style='StatusCommandThree.TButton')
        self.StatusCommandThree.place(relx=0.038, rely=0.45, relwidth=0.103, relheight=0.1)

        self.style.configure('StatusCommandTwo.TButton',font=('宋体',9))
        self.StatusCommandTwo = Button(self.StatusFrame, text='StatusCommand', command=self.StatusCommandTwo_Cmd, style='StatusCommandTwo.TButton')
        self.StatusCommandTwo.place(relx=0.038, rely=0.293, relwidth=0.103, relheight=0.1)

        self.style.configure('StatusCommandOne.TButton',font=('宋体',9))
        self.StatusCommandOne = Button(self.StatusFrame, text='StatusCommand', command=self.StatusCommandOne_Cmd, style='StatusCommandOne.TButton')
        self.StatusCommandOne.place(relx=0.038, rely=0.137, relwidth=0.103, relheight=0.1)

        self.LogListVar = StringVar(value='')
        self.LogListFont = Font(font=('宋体',9))
        self.LogList = Listbox(self.StatusFrame, listvariable=self.LogListVar, font=self.LogListFont)
        self.LogList.place(relx=0.178, rely=0.137, relwidth=0.777, relheight=0.626)

        self.style.configure('ServiceCommandFive.TButton',font=('宋体',9))
        self.ServiceCommandFive = Button(self.ServiceFrame, text='ServiceCommand', command=self.ServiceCommandFive_Cmd, style='ServiceCommandFive.TButton')
        self.ServiceCommandFive.place(relx=0.213, rely=0.361, relwidth=0.573, relheight=0.049)

        self.style.configure('ServiceCommandFour.TButton',font=('宋体',9))
        self.ServiceCommandFour = Button(self.ServiceFrame, text='ServiceCommand', command=self.ServiceCommandFour_Cmd, style='ServiceCommandFour.TButton')
        self.ServiceCommandFour.place(relx=0.213, rely=0.285, relwidth=0.573, relheight=0.049)

        self.style.configure('ServiceCommandThree.TButton',font=('宋体',9))
        self.ServiceCommandThree = Button(self.ServiceFrame, text='ServiceCommand', command=self.ServiceCommandThree_Cmd, style='ServiceCommandThree.TButton')
        self.ServiceCommandThree.place(relx=0.213, rely=0.209, relwidth=0.573, relheight=0.049)

        self.style.configure('ServiceCommandTwo.TButton',font=('宋体',9))
        self.ServiceCommandTwo = Button(self.ServiceFrame, text='ServiceCommand', command=self.ServiceCommandTwo_Cmd, style='ServiceCommandTwo.TButton')
        self.ServiceCommandTwo.place(relx=0.213, rely=0.133, relwidth=0.573, relheight=0.049)

        self.style.configure('ServiceCommandOne.TButton',font=('宋体',9))
        self.ServiceCommandOne = Button(self.ServiceFrame, text='ServiceCommand', command=self.ServiceCommandOne_Cmd, style='ServiceCommandOne.TButton')
        self.ServiceCommandOne.place(relx=0.213, rely=0.057, relwidth=0.573, relheight=0.049)


class Application(Application_ui):
    #这个类实现具体的事件处理回调函数。界面生成代码在Application_ui中。
    def __init__(self, master=None):
        Application_ui.__init__(self, master)

    def StatusCommandFive_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("StatusCommandFive_Cmd",0,0)
        pass

    def StatusCommandFour_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("StatusCommandFour_Cmd",0,0)
        pass

    def StatusCommandThree_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("StatusCommandThree_Cmd",0,0)
        pass

    def StatusCommandTwo_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("StatusCommandTwo_Cmd",0,0)
        pass

    def StatusCommandOne_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("StatusCommandOne_Cmd",0,0)
        pass

    def ServiceCommandFive_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("ServiceCommandFive_Cmd",0,0)
        pass

    def ServiceCommandFour_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("ServiceCommandFour_Cmd",0,0)
        pass

    def ServiceCommandThree_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("ServiceCommandThree_Cmd",0,0)
        pass

    def ServiceCommandTwo_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("ServiceCommandTwo_Cmd",0,0)
        pass

    def ServiceCommandOne_Cmd(self, event=None):
        #TODO, Please finish the function here!
        self.UI_Log("ServiceCommandOne_Cmd",0,0)
        pass



    def UI_Log(self,logstr,level,index):
        cindex= index  if index>0 else 0
        clevel= level  if level else 0
        clogstr= logstr  if logstr else ""
        for i in range(0,cindex):
            clogstr="  "+clogstr

      
        self.LogList.insert(END,clogstr)
      
 


    def UI_Command(self,commandstr):
        self.UI_Log(commandstr,0,0)


if __name__ == "__main__":
    top = Tk()
    Application(top).mainloop()
    try: top.destroy()
    except: pass
