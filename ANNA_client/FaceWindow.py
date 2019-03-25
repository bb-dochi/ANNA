from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
import cv2
import socket
import os

from MainWindow import MainWindow

form_face = uic.loadUiType("UI\\faceRecognize.ui")[0]

su_stop = False
t_stop = False

s_socket = None
IsSuccess = False
USERID = None
#회원가입용 스레드
class Thread_SU(QThread):
    changePixmap = pyqtSignal(QImage)
    def thControll(self,type):
        global su_stop
        su_stop = type
    def run(self):
        cap = cv2.VideoCapture(0)
        while True:
            if su_stop:
                 break
            ret, frame = cap.read()
            count = 0
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
                p = convertToQtFormat.scaled(390, 360, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)

#자동 로그인용 스레드
class Thread(QThread):
    facewindow = None
    changePixmap = pyqtSignal(QImage)
    def run(self):
        cap = cv2.VideoCapture(0)
        face_cascade = cv2.CascadeClassifier()
        face_cascade.load('haarcascade_frontalface_alt.xml')

        while True:
            if t_stop:
                 break
            ret, frame = cap.read()
            count = 0
            if ret:
                rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                faces = face_cascade.detectMultiScale(rgbImage, 1.8, 2, 0, (50, 50))

                #원본 이미지에 얼굴 인식된 부분 표시
                for (x,y,w,h) in faces:
                    cx = int(x+(w/2))
                    cy = int(y+(h/2))
                    cr = int(w/2)
                    cv2.circle(rgbImage,(cx,cy),cr,(0,255,0),3)
                    cv2.imwrite('face.png', frame)
                    self.sendFace()
                    break

                convertToQtFormat = QImage(rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
                p = convertToQtFormat.scaled(390, 360, Qt.KeepAspectRatio)
                self.changePixmap.emit(p)

    #서버랑 연결해 얼굴인식 로그인
    def sendFace(self):
        global t_stop
        t_stop = True

        global s_socket
        s_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s_socket.connect(('18.220.43.141',5002))

        #저장한 이미지 열기
        file = open("face.png", "rb")
        img_size = os.path.getsize("face.png")
        img = file.read(img_size)
        file.close()

        #이미지 전송
        s_socket.sendall(img)
        data = 'finish'
        s_socket.send(data.encode())

        #응답 대기
        data = s_socket.recv(1024).decode().strip()

        #받은 값이 None이 아니면 (id를 받은거임)
        if data is not None:
            global IsSuccess
            global USERID
            IsSuccess = True
            USERID = data #아이디 설정
        else:
            print('자동로그인 실패')
            self.facewindow

        s_socket.close()

class FaceWindow(QMainWindow, form_face):
    loginwindow = None
    def __init__(self,window):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("ANNA")
        self.loginwindow = window
        self.initUI()

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.label.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        self.label = QLabel(self)
        self.label.move(30, 30)
        self.label.resize(390, 360)
        th = Thread(self)
        th.changePixmap.connect(self.setImage)
        th.facewindow = self
        th.start()

    def th_open(self):
        global t_stop
        t_stop = False

    #자동로그인 될때까지 계속 대기
    def openmain(self):
        while not IsSuccess: #성공하면 끝나는 무한루프
            continue
        self.loginwindow.hide()
        self.newWindow = MainWindow(USERID)
        self.newWindow.show()
        self.hide()

    def closeWindow(self):
        global t_stop
        t_stop = True
        self.close()
