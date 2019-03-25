# coding: utf-8

import sys
import os
from PyQt5 import QtCore, QtGui, uic, QtWidgets
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from MainWindow import MainWindow
from FaceWindow import FaceWindow, Thread_SU
from win10toast import ToastNotifier
import cv2
import numpy as np
import threading
import time
import queue

import uuid
import pymysql

form_login = uic.loadUiType("UI\\loginUI.ui")[0]
form_signup = uic.loadUiType("UI\\signupUI.ui")[0]

#회원가입 페이지로드
class SignUpWindow(QMainWindow, form_signup):
    first = True
    isStart = False
    th = None
    image = None
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("ANNA")
        self.th = Thread_SU(self)
        self.th.changePixmap.connect(self.setImage)

    def signUp(self): #회원가입 버튼 클릭
        username = self.userName.text()
        userid = self.userId.text()
        userpw = self.userPasswd.text()
        userpwC = self.userPasswdC.text()
        userphone = self.userPhone.text()

        checkid=0
        checkpw=0

        conn = dbConnect()
        curs = conn.cursor()
        sql = "select id from userDB"
        curs.execute(sql)

        rows = curs.fetchall()
        print(rows)
        for item in rows:
            if userid == item[0]:
                print(item[0])
                self.showMessage("이미 존재하는 아이디입니다.  ")
                checkid=0
                break
            else:
                checkid=1

        if userpw == userpwC:
            checkpw=1
        else:
            checkpw=0
            self.showMessage("비밀번호와 비밀번호확인이 일치하지 않습니다.  ")

        print(checkid + checkpw)
        if checkid == 1 and checkpw == 1:
            QLabel.pixmap(self.facelbl).save("user_"+userid+".png", "PNG")
            imgblob = open("user_"+userid+".png", 'rb').read()

            conn = dbConnect()
            curs = conn.cursor()
            sql = "insert into userDB(name, id, pw, pw_check, phone, image, mac) values(%s, %s, %s, %s, %s, %s, %s)"
            curs.execute(sql, (username, userid, userpw, userpwC, userphone, imgblob, self.get_mac()))
            print("signup success!!!!")

            self.th.thControll(self.isStart)
            self.isStart = False
            #os.remove('user_'+userid+'.png')
            conn.commit()
            conn.close()

        #로그인화면으로 이동
        self.newWindow = MyWindow()
        self.newWindow.show()
        self.hide()

    def startCamera(self):
        if self.first: #맨 처음 눌렀을 때 스레드 실행
            self.th.start()
            self.isStart = True
            self.first = False
        else:
            if self.isStart: #켜져있을 때 버튼 클릭 시 멈춤
                self.th.thControll(self.isStart)
                self.isStart = False
            else :#안켜져있을 때 버튼 클릭 시 켜짐
                self.th.thControll(self.isStart)
                self.isStart = True


    @pyqtSlot(QImage)
    def setImage(self, image):
        self.facelbl.setPixmap(QPixmap.fromImage(image))

    #화면 종료 시 이벤트
    def closeEvent(self, event):
        global running
        running = False

    #alert 띄우는 메소드
    def showMessage(self,message):
        msg = QMessageBox()
        msg.setText(message)
        msg.setWindowTitle("ANNA Information")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    #맥주소 얻기
    def get_mac(self):
        mac_num = hex(uuid.getnode()).replace('0x', '').upper()
        mac = '-'.join(mac_num[i: i + 2] for i in range(0, 11, 2))
        return mac

#로그인 페이지 로드
class MyWindow(QMainWindow, form_login):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("ANNA")

    #자동로그인 버튼
    def openFaceWindow(self):
        self.facewindow = FaceWindow(self)
        self.facewindow.show()
        #자동로그인 대기 함수 실행
        self.facewindow.openmain()

    def handleSignin(self): #로그인 버튼 클릭
        id = self.userId.text()
        pw = self.userPasswd.text()

        conn = dbConnect()
        curs = conn.cursor()
        sql = "select id,pw from userDB"
        curs.execute(sql)

        rows = curs.fetchall()
        for item in rows:
            if id == item[0] :
                if pw == item[1]:
                    print("login success")
                    conn.close()

                    #메인으로 이동
                    self.newWindow = MainWindow(id)
                    self.newWindow.show()
                    self.hide()
                    break

    def handleSignup(self):
        #회원가입 페이지로 이동
        self.newWindow = SignUpWindow()
        self.newWindow.show()
        self.hide()


def dbConnect():
    conn = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
    return conn

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MyWindow()
    myWindow.show()
    app.exec_()
