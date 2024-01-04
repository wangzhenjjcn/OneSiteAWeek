VERSION 5.00
Begin VB.Form Myazure 
   Caption         =   "MyazureToolBox"
   ClientHeight    =   12915
   ClientLeft      =   120
   ClientTop       =   465
   ClientWidth     =   23760
   LinkTopic       =   "Form1"
   ScaleHeight     =   12915
   ScaleWidth      =   23760
   StartUpPosition =   1  '所有者中心
   Begin VB.Frame ControlFrame 
      Caption         =   "Control"
      Height          =   6135
      Left            =   4200
      TabIndex        =   2
      Top             =   6480
      Width           =   18855
   End
   Begin VB.Frame StatusFrame 
      Caption         =   "Status"
      Height          =   6135
      Left            =   4200
      TabIndex        =   1
      Top             =   120
      Width           =   18855
      Begin VB.TextBox CommandText 
         Height          =   495
         Left            =   3360
         TabIndex        =   14
         Top             =   4800
         Width           =   14655
      End
      Begin VB.CommandButton StatusCommandFive 
         Caption         =   "StatusCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   8
         Top             =   4680
         Width           =   1935
      End
      Begin VB.CommandButton StatusCommandFour 
         Caption         =   "StatusCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   7
         Top             =   3720
         Width           =   1935
      End
      Begin VB.CommandButton StatusCommandThree 
         Caption         =   "StatusCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   6
         Top             =   2760
         Width           =   1935
      End
      Begin VB.CommandButton StatusCommandTwo 
         Caption         =   "StatusCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   5
         Top             =   1800
         Width           =   1935
      End
      Begin VB.CommandButton StatusCommandOne 
         Caption         =   "StatusCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   4
         Top             =   840
         Width           =   1935
      End
      Begin VB.ListBox LogList 
         Height          =   3840
         ItemData        =   "Myazure.frx":0000
         Left            =   3360
         List            =   "Myazure.frx":0002
         TabIndex        =   3
         Top             =   840
         Width           =   14655
      End
   End
   Begin VB.Frame ServiceFrame 
      Caption         =   "Service"
      Height          =   12615
      Left            =   360
      TabIndex        =   0
      Top             =   120
      Width           =   3375
      Begin VB.CommandButton ServiceCommandFive 
         Caption         =   "ServiceCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   13
         Top             =   4560
         Width           =   1935
      End
      Begin VB.CommandButton ServiceCommandFour 
         Caption         =   "ServiceCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   12
         Top             =   3600
         Width           =   1935
      End
      Begin VB.CommandButton ServiceCommandThree 
         Caption         =   "ServiceCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   11
         Top             =   2640
         Width           =   1935
      End
      Begin VB.CommandButton ServiceCommandTwo 
         Caption         =   "ServiceCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   10
         Top             =   1680
         Width           =   1935
      End
      Begin VB.CommandButton ServiceCommandOne 
         Caption         =   "ServiceCommand"
         Height          =   615
         Left            =   720
         TabIndex        =   9
         Top             =   720
         Width           =   1935
      End
   End
End
Attribute VB_Name = "Myazure"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = False
