VERSION 5.00
Begin VB.Form VideoDownloader 
   Caption         =   "Ӱ������"
   ClientHeight    =   12750
   ClientLeft      =   60
   ClientTop       =   405
   ClientWidth     =   23250
   LinkTopic       =   "Ӱ������"
   ScaleHeight     =   850
   ScaleMode       =   3  'Pixel
   ScaleWidth      =   1550
   StartUpPosition =   2  '��Ļ����
   Begin VB.Frame FrameDetial 
      Caption         =   "ӰƬ����"
      Height          =   12375
      Left            =   9480
      TabIndex        =   7
      Top             =   120
      Width           =   13455
      Begin VB.ComboBox ComboDetialType 
         Height          =   300
         ItemData        =   "VideoDownloader.frx":0000
         Left            =   2520
         List            =   "VideoDownloader.frx":0007
         TabIndex        =   18
         Text            =   "��ѡ��"
         Top             =   1800
         Width           =   6615
      End
      Begin VB.CommandButton CommandCopyListMag 
         Caption         =   "��������"
         Height          =   615
         Left            =   9840
         TabIndex        =   17
         Top             =   4320
         Width           =   2415
      End
      Begin VB.CommandButton CommandDownloadAllList 
         Caption         =   "��������"
         Height          =   615
         Left            =   9840
         TabIndex        =   16
         Top             =   3480
         Width           =   2415
      End
      Begin VB.CommandButton CommandDownloadSelected 
         Caption         =   "����ѡ��"
         Height          =   615
         Left            =   9840
         TabIndex        =   15
         Top             =   2640
         Width           =   2415
      End
      Begin VB.CommandButton CommandDetialOpenEpisodes 
         Caption         =   "�򿪲���"
         Height          =   615
         Left            =   10920
         TabIndex        =   14
         Top             =   960
         Width           =   2415
      End
      Begin VB.CommandButton CommandDetialDownloadAllEpisodes 
         Caption         =   "��������"
         Height          =   615
         Left            =   8400
         TabIndex        =   13
         Top             =   960
         Width           =   2415
      End
      Begin VB.ListBox ListDownloadSource 
         Height          =   6900
         ItemData        =   "VideoDownloader.frx":0017
         Left            =   960
         List            =   "VideoDownloader.frx":001E
         TabIndex        =   12
         Top             =   2640
         Width           =   8175
      End
      Begin VB.CommandButton CommandDetialDownloadCurrentEpisodes 
         Caption         =   "���ص�ǰ"
         Height          =   615
         Left            =   5880
         TabIndex        =   11
         Top             =   960
         Width           =   2370
      End
      Begin VB.ComboBox ComboDetialPlaySourceEpisodes 
         Height          =   300
         ItemData        =   "VideoDownloader.frx":002E
         Left            =   2520
         List            =   "VideoDownloader.frx":0035
         TabIndex        =   10
         Text            =   "��ѡ��"
         Top             =   1320
         Width           =   2295
      End
      Begin VB.ComboBox ComboDetialPlaySource 
         Height          =   300
         ItemData        =   "VideoDownloader.frx":0045
         Left            =   2520
         List            =   "VideoDownloader.frx":004C
         TabIndex        =   9
         Text            =   "��ѡ��"
         Top             =   960
         Width           =   2295
      End
      Begin VB.Label LabelDetialDownloadType 
         Caption         =   "ѡ�����������ȣ�"
         Height          =   495
         Left            =   240
         TabIndex        =   27
         Top             =   1800
         Width           =   1935
      End
      Begin VB.Label LabelDetialDrictor 
         Caption         =   "���ݣ���������ʾ"
         Height          =   375
         Left            =   7320
         TabIndex        =   26
         Top             =   480
         Width           =   2295
      End
      Begin VB.Label LabelDetialZone 
         Caption         =   "��������������ʾ"
         Height          =   375
         Left            =   4920
         TabIndex        =   25
         Top             =   480
         Width           =   2295
      End
      Begin VB.Label LabelDetialSort 
         Caption         =   "���ࣺ��������ʾ"
         Height          =   375
         Left            =   2520
         TabIndex        =   24
         Top             =   480
         Width           =   2295
      End
      Begin VB.Label LabelDetialPlaylist 
         Caption         =   "���ŵ�ַ��"
         Height          =   495
         Left            =   240
         TabIndex        =   23
         Top             =   1080
         Width           =   1935
      End
      Begin VB.Label LabelDetialIntro 
         Caption         =   "��飺��������ʾ"
         Height          =   2295
         Left            =   9840
         TabIndex        =   22
         Top             =   7080
         Width           =   2535
      End
      Begin VB.Label LabelDetialRatings 
         Caption         =   "���֣���������ʾ"
         Height          =   615
         Left            =   9840
         TabIndex        =   21
         Top             =   6240
         Width           =   2535
      End
      Begin VB.Label LabelDetialUpdateTime 
         Caption         =   "����ʱ�䣺��������ʾ"
         Height          =   495
         Left            =   9840
         TabIndex        =   20
         Top             =   5400
         Width           =   2655
      End
      Begin VB.Label LabelDetialIntroduction 
         Caption         =   "������ܣ���������ʾ"
         Height          =   1695
         Left            =   960
         TabIndex        =   19
         Top             =   9840
         Width           =   12015
      End
      Begin VB.Label LabelDetialName 
         Caption         =   "���ƣ���������ʾ"
         Height          =   375
         Left            =   240
         TabIndex        =   8
         Top             =   480
         Width           =   2175
      End
   End
   Begin VB.Frame FrameSearchResault 
      Caption         =   "�������"
      Height          =   11175
      Left            =   120
      TabIndex        =   4
      Top             =   1320
      Width           =   9135
      Begin VB.CommandButton CommandNextpage 
         Caption         =   "��һҳ"
         Height          =   615
         Left            =   2520
         TabIndex        =   35
         Top             =   240
         Width           =   1215
      End
      Begin VB.CommandButton CommandLastPage 
         Caption         =   "��һҳ"
         Height          =   615
         Left            =   1200
         TabIndex        =   34
         Top             =   240
         Width           =   1215
      End
      Begin VB.CommandButton CommandCheckDetial 
         Caption         =   "�鿴����"
         Height          =   495
         Left            =   5640
         TabIndex        =   29
         Top             =   9840
         Width           =   2655
      End
      Begin VB.PictureBox PictureDetialBox 
         BackColor       =   &H8000000A&
         Height          =   4695
         Left            =   360
         ScaleHeight     =   309
         ScaleMode       =   3  'Pixel
         ScaleWidth      =   205
         TabIndex        =   28
         Top             =   4800
         Width           =   3135
      End
      Begin VB.ListBox ListResalut 
         BackColor       =   &H00C0C0C0&
         Height          =   3300
         ItemData        =   "VideoDownloader.frx":005C
         Left            =   360
         List            =   "VideoDownloader.frx":005E
         TabIndex        =   5
         Top             =   960
         Width           =   8295
      End
      Begin VB.Label LabelResaultDirector 
         Caption         =   "���ݣ���������ʾ"
         Height          =   375
         Left            =   3720
         TabIndex        =   33
         Top             =   5040
         Width           =   4455
      End
      Begin VB.Label LabelResaultStar 
         Caption         =   "���ݣ���������ʾ"
         Height          =   1335
         Left            =   3720
         TabIndex        =   32
         Top             =   5640
         Width           =   4455
      End
      Begin VB.Label LabelResaultIntro 
         Caption         =   "��飺��������ʾ"
         Height          =   2055
         Left            =   3720
         TabIndex        =   31
         Top             =   7200
         Width           =   4455
      End
      Begin VB.Label LabelResaultEpisode 
         Caption         =   "��������������ʾ"
         Height          =   615
         Left            =   480
         TabIndex        =   30
         Top             =   9720
         Width           =   2655
      End
      Begin VB.Label LabelResaultList 
         Caption         =   "����б�"
         Height          =   255
         Left            =   240
         TabIndex        =   6
         Top             =   360
         Width           =   1095
      End
   End
   Begin VB.Frame FrameSearch 
      Caption         =   "����Ӱ��"
      Height          =   1095
      Left            =   120
      TabIndex        =   0
      Top             =   120
      Width           =   9135
      Begin VB.CommandButton CommandSearch 
         Caption         =   "����"
         Height          =   615
         Left            =   6720
         TabIndex        =   3
         Top             =   240
         Width           =   2175
      End
      Begin VB.TextBox TextInput 
         Height          =   510
         Left            =   1560
         TabIndex        =   2
         Top             =   240
         Width           =   4935
      End
      Begin VB.Label LabelKeyword 
         Caption         =   "�ؼ��֣�"
         Height          =   375
         Left            =   240
         TabIndex        =   1
         Top             =   360
         Width           =   1095
      End
   End
End
Attribute VB_Name = "VideoDownloader"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
