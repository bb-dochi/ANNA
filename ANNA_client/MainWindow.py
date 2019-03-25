# coding: utf-8
import os
import io
import sys
import socket,threading
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic
from win10toast import ToastNotifier
from calendarCtrl import Calendar,CalendarWindow
from ANNA_chatbot import ANNA

#data관련 import
import pymysql
import datetime
import pytagcloud
from konlpy.tag import Twitter
from collections import Counter
import re
import sqlite3
from dateutil.relativedelta import relativedelta
import requests
from bs4 import BeautifulSoup


sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding = 'utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding = 'utf-8')

form_class = uic.loadUiType("UI\\mainUI.ui")[0]
trayimg = "UI\\trayIcon.png" #트레이아이콘 이미지 경로
toastimg = "UI\\toastLogo.png" #토스트아이콘 이미지 경로

s_socket = None
starttime = None
USERID = None

#메인 페이지로드
class MainWindow(QMainWindow, form_class):
    tray_icon = None
    cal = None
    #(수정2)지워도됨
    #log_starttime = None
    #log_endtime = None
    def __init__(self,id):
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("ANNA")
        self.mainTab.setCurrentIndex(0)

        #유저 전역변수 설정
        global USERID
        USERID = id
        self.lblwelcome.setText(USERID+"님, 환영합니다.")

        #서버 접속
        global s_socket
        s_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s_socket.connect(('18.220.43.141',5001))

        data = 'pc'
        s_socket.sendall(data.encode())
        threading.Thread(target=self.serverConnect).start()

        #시작 로그 설정
        global starttime
        starttime = datetime.datetime.now()
        print(starttime)

        #캘린더 오늘일정 설정
        self.cal = Calendar(USERID)
        date = self.calendarWidget.selectedDate().toPyDate()
        calList = self.cal.getSchedule(date)
        self.scheduleList.setPlainText(calList);

        #데이터 불러오기
        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql2 = con_mysql.cursor()
        sql = "select starttime, endtime from user_log where id = '"+USERID+"' order by num desc limit 1"
        cursor_mysql2.execute(sql)
        log_rows = cursor_mysql2.fetchone()

        '''(수정2) 지워도됨
        if log_rows is not None:
            self.log_starttime = log_rows[0]
            self.log_endtime = log_rows[1]
        '''

        self.visitTimeOfData()
        self.crawling_userkeyword_news()
        self.crawling_news()

        # 트레이아이콘 설정
        self.tray_icon = QSystemTrayIcon(self)
        self.icon = QIcon(trayimg)
        self.tray_icon.setIcon(self.icon)

        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        hide_action = QAction("Hide", self)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(self.quit)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.annaChatbot)

        #키워드 시각화 label reset 및 pixmap 설정 (추가)(수정2)
        filename = "UI/wordcloud_" + USERID + ".jpg"
        self.label_3.clear()
        self.label_3.setPixmap(QPixmap(filename))

        #url 내역 가져와서 뿌려주기(수정2)
        cursor_url = con_mysql.cursor()
        sql = "select url_title, visit_url from user_url where id = '"+USERID+"' order by visit_count desc, url_date desc limit 5"
        cursor_url.execute(sql)
        result_url = cursor_url.fetchall()
        con_mysql.close()

        url_list = [0 for row in range(5)]
        num=0
        for url_one in result_url:
            url_list[num] = '<a href = "'+url_one[1]+'">' +url_one[0]+ '</a>'
            num = num + 1

        #방문접속내역! (추가)
        if len(url_list) > 0 :
            self.label_30.setText(str(url_list[0]))
            self.label_30.setOpenExternalLinks(True)
            self.label_31.setText(str(url_list[1]))
            self.label_31.setOpenExternalLinks(True)
            self.label_32.setText(str(url_list[2]))
            self.label_32.setOpenExternalLinks(True)
            self.label_33.setText(str(url_list[3]))
            self.label_33.setOpenExternalLinks(True)
            self.label_34.setText(str(url_list[4]))
            self.label_34.setOpenExternalLinks(True)

    #트레이아이콘 클릭시 챗봇실행
    def annaChatbot(self, event):
        if event == QSystemTrayIcon.Trigger:
            anna = ANNA()
            anna.start(self)

    #닫기 버튼 눌렀을때 실행되는 메소드
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "ANNA",
            "트레이아이콘으로 최소화되었습니다.\n아이콘 우클릭 > 종료 시 종료가능",
            QIcon(trayimg),
            2000
        )

    #트레이아이콘 메세지
    def showTrayMessage(self, message):
        self.tray_icon.showMessage(
            "ANNA",
            message,
            QIcon(toastimg),
            2000
        )

    #메인 탭 바꿔주는 메소드
    def setTab(self,index):
        self.mainTab.setCurrentIndex(index)

    #캘린더 위젯 클릭 시 일정 가져오기
    def getSchedule(self):
        week = ['월','화','수','목','금','토','일']
        date = self.calendarWidget.selectedDate().toPyDate()
        str_date = str(date)+" ("+week[date.weekday()]+")"
        self.lblselectedDate.setText(str_date)

        calList = self.cal.getSchedule(date)
        self.scheduleList.setPlainText(calList);

    #일정추가 메소드
    def addSchedule(self):
        self.newWindow = CalendarWindow(USERID)
        self.newWindow.show()

    #서버랑 통신(폰알람/ 데이터저장/ 얼굴인식 통로)
    def serverConnect(self):
        global s_socket

        while True:
            data = s_socket.recv(1024).decode().strip()
            if data == 'smsAlarm':
                self.showTrayMessage('메세지가 왔습니다.\n휴대폰을 확인해보세요.')
            elif data == 'callAlarm':
                self.showTrayMessage('전화가 왔습니다.\n휴대폰을 확인해보세요.')
        s_socket.close()

    #가장 최근 LOG 키워드 저장, 명사 추출, 시각화
    def kewordOfData(self, endtime):
        os.system("taskkill.exe /f /im chrome.exe")
        con_sqlite = sqlite3.connect('C:\\Users\\user\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History')
        cursor_sqlite = con_sqlite.cursor()
        cursor_sqlite.execute("SELECT term, url_id FROM keyword_search_terms ORDER BY url_id DESC")

        cursor_sqlite2 = con_sqlite.cursor()

        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql = con_mysql.cursor()
        cursor_mysql2 = con_mysql.cursor()
        #가장 최근 키워드 명사 추출 (추가)
        all_list = [[0 for col in range(2)] for row in range(500)]
        count = 0
        col = 0
        while count < 100:
            count = count + 1
            data = cursor_sqlite.fetchone()
            str = data[0]

            url_id = int(data[1])

            cursor_sqlite2.execute("SELECT last_visit_time FROM urls WHERE id = ?", (url_id, ))
            date_rows = cursor_sqlite2.fetchone()
            datelog = int(date_rows[0])
            keyword_date = self.date_from_webkit(int(date_rows[0]))

            #(수정2)
            global starttime
            if keyword_date >= starttime and keyword_date <= endtime:
                tags = self.get_tags(str, keyword_date, 50)
            else:
                continue

            for tag in tags:
                noun = tag['tag']
                noun_date = tag['date']
                all_list[col][0] = noun
                all_list[col][1] = noun_date
                col = col + 1

        #추출한 명사 db저장 (추가)
        cloudnoun = []
        i = 0
        for all0, all1 in all_list:
            if all0 != 0:
                cloudnoun.append(all0)
                sql = "select * from user_keyword where keyword = '"+all0+"'"
                cursor_mysql.execute(sql)
                double_rows = cursor_mysql.fetchone()

                if len(all0) == 1:
                    continue

                if all1 is None:
                    continue

                if double_rows is None:
                    i = i + 1
                    #(수정)
                    cursor_mysql2.execute('insert into user_keyword(id, keyword, keyword_date, count) values(%s, %s, %s, 1)', (USERID, all0, all1))
                else:
                    print(double_rows)
                    cursor_mysql2.execute('update user_keyword set count = count + 1 where keyword = %s', (all0,))
                con_mysql.commit()

        #키워드 시각화 파일 저장 (추가)
        #보완 : 1달 지난 키워드 지워버리기 ㅜㅜ
        #con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql3 = con_mysql.cursor()
        dateterm = datetime.datetime.now() - relativedelta(months=1)
        sql = "select keyword, count from user_keyword where id = '"+USERID+"' and keyword_date >= %s order by count desc limit 20"
        cursor_mysql3.execute(sql, (dateterm,))
        rows = cursor_mysql3.fetchall()
        self.write_cloud(rows)
        con_mysql.close()

    #방문 URL 가져오는 메소드
    def visitURLOfData(self, endtime):
        #url정보 가져오고 저장
        #url 데이터베이스 접근

        con_sqlite = sqlite3.connect('C:\\Users\\user\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\History')
        cursor_sqlite = con_sqlite.cursor()
        cursor_sqlite.execute("SELECT url, title, visit_count, last_visit_time FROM urls ORDER BY id DESC")

        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql = con_mysql.cursor()
        #(수정)
        cursor_mysql2 = con_mysql.cursor()

        count = 0
        datacount = 0
        while count < 1000:
            count = count + 1
            data = cursor_sqlite.fetchone()
            urls_date = self.date_from_webkit(data[3])

            urls_url = data[0]
            urls_title = data[1]
            urls_visitcnt = data[2]

            cursor_mysql.execute("select * from user_url where id = %s and url_title = %s", (USERID, urls_title, ))
            double_rows = cursor_mysql.fetchone()

            #만일, 중복값이 있으면 if문 처리 !(수정)(수정2)
            global starttime
            if double_rows is None:
                if urls_date >= starttime and urls_date <= endtime:
                    datacount = datacount + 1
                    cursor_mysql2.execute('insert into user_url(id, url_date, visit_url, url_title, visit_count) values(%s, %s, %s, %s, %s)', (USERID, urls_date, urls_url, urls_title, urls_visitcnt))
                    con_mysql.commit()
                    if datacount == 5:
                        break
                else:
                    continue
            else:
                continue
        #(수정2) while문 밑에 내용은 init 메서드 밑부분에 추가!!

    #최근 방문내역 가져와 table에 추가
    def visitTimeOfData(self):
        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_log = con_mysql.cursor()
        sql = "select starttime, endtime from user_log where id = '"+USERID+"' order by num desc limit 7"
        cursor_log.execute(sql)
        log_list = cursor_log.fetchall()

        i = 0
        for log in log_list:
            self.table.setItem(i, 0, QTableWidgetItem(log[0].strftime('%m/%d %H:%M')))
            self.table.setItem(i, 1, QTableWidgetItem(log[1].strftime('%m/%d %H:%M')))
            i = i + 1

    #이시각 뉴스 크롤링 (추가)
    def crawling_news(self):
        html = requests.get('https://news.naver.com/').text
        soup = BeautifulSoup(html, 'html.parser')

        title_list = soup.select('.newsnow_tx_inner a')

        strlist = [0 for row in range(15)]

        num = 0
        for title in title_list:
            strlist[num] = '<a href = "'+title.get('href')+'">' +title.text+ '</a>'
            print(title.text)
            print(title.get('href'))
            print()
            num = num + 1

        #크롤링 결과 ui upload
        self.label_14.setText(strlist[0])
        self.label_14.setOpenExternalLinks(True)
        self.label_15.setText(strlist[1])
        self.label_15.setOpenExternalLinks(True)
        self.label_16.setText(strlist[2])
        self.label_16.setOpenExternalLinks(True)
        self.label_17.setText(strlist[3])
        self.label_17.setOpenExternalLinks(True)
        self.label_18.setText(strlist[4])
        self.label_18.setOpenExternalLinks(True)
        self.label_19.setText(strlist[5])
        self.label_19.setOpenExternalLinks(True)
        self.label_20.setText(strlist[6])
        self.label_20.setOpenExternalLinks(True)

    #사용자 맞춤형 뉴스 (추가)
    def crawling_userkeyword_news(self):
        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql = con_mysql.cursor()
        sql = "select keyword from user_keyword where id = '"+USERID+"' order by count desc limit 3"
        cursor_mysql.execute(sql)
        rows = cursor_mysql.fetchall()

        strlist = [0 for row in range(10)]

        keywordnum = 0
        num = 0
        for keyword in rows:
            keywordnum += 1
            word = keyword[0]
            url = "https://search.daum.net/search?w=news&nil_search=btn&DA=NTB&enc=utf8&cluster=y&cluster_page=1&q=" + word

            html = requests.get(url).text
            soup = BeautifulSoup(html, 'html.parser')

            title_list = soup.select('#clusterResultUL li > div > div > div > a')

            #만약 키워드 관련 뉴스가 없을 때 제외
            if title_list == []:
                keywordnum -=1
                continue

            strlist[num] = word

            cnt = 0
            for title in title_list:
                num += 1
                cnt += 1
                strlist[num] = '<a href = "'+title.get('href')+'">' +title.text+ '</a>'
                if cnt == 2:
                    break
            num += 1

            if keywordnum == 3:
                break

        #맞춤형 뉴스 크롤링?! 노가다2 ^^ (추가)
        self.label_21.setText(str(strlist[0]))
        self.label_22.setText(str(strlist[1]))
        self.label_22.setOpenExternalLinks(True)
        self.label_23.setText(str(strlist[2]))
        self.label_23.setOpenExternalLinks(True)
        self.label_24.setText(str(strlist[3]))
        self.label_25.setText(str(strlist[4]))
        self.label_25.setOpenExternalLinks(True)
        self.label_26.setText(str(strlist[5]))
        self.label_26.setOpenExternalLinks(True)
        self.label_27.setText(str(strlist[6]))
        self.label_28.setText(str(strlist[7]))
        self.label_28.setOpenExternalLinks(True)
        self.label_29.setText(str(strlist[8]))
        self.label_29.setOpenExternalLinks(True)

    #검색어 -> 명사(키워드) 추출 (추가)
    def get_tags(self, text, date, ntags=100):
        spliter = Twitter()# konlpy의 Twitter객체
        frequency = {}
        nouns = spliter.nouns(text)# nouns 함수를 통해서 text에서 명사만 분리/추출
        match_pattern = re.findall(r'\b[a-zA-Z]{3,15}\b', text)
        count = Counter(nouns)# Counter객체를 생성하고 참조변수 nouns할당
        return_list = []  # 명사 빈도수 저장할 변수

        for word in match_pattern:
            count1 = frequency.get(word, 0)
            frequency[word] = count1 + 1

        frequency_list = frequency.keys()
        for words in frequency_list:
            temp_en = {'tag': words, 'date':date}
            return_list.append(temp_en)

        for n,c in count.most_common(ntags):
            temp_ko = {'tag': n, 'date': date}
            return_list.append(temp_ko)
        return return_list

    #키워드 -> 그림 (추가)
    def write_cloud(self, data):
        taglist = pytagcloud.make_tags(data, maxsize=80, minsize=30)
        print(taglist)
        global USERID
        #(수정2) 유저별로 그림저장
        filename = "UI/wordcloud_" + USERID + ".jpg"
        pytagcloud.create_tag_image(taglist, filename, size=(600, 600), fontname='Noto Sans CJK', rectangular=True)

    #마이크로초 -> 날짜 (추가)
    def date_from_webkit(self, webkit_timestamp):
        resultTime = None;
        #크롬 시간은 1601년1월1일 기준으로 마이크로초로 변환하여 저장해놓음
        epoch_start = datetime.datetime(1601,1,1)
        delta = datetime.timedelta(microseconds=int(webkit_timestamp)+32400000000)#9시간 차로 인해 9시간 더해줌
        result_test = epoch_start + delta
        if datetime.date.today().month - (epoch_start + delta).month == 1:
            if datetime.date.today().day - (epoch_start + delta).day == 0 :
                resultTime = (epoch_start + delta)
            else:
                resultTime = (epoch_start + delta)
        elif datetime.date.today().month - (epoch_start + delta).month == 0:
            resultTime = (epoch_start + delta)
        else:
            resultTime = (epoch_start + delta)
        return resultTime

    #실제 앱종료 메소드
    def quit(self):
        global USERID
        endtime = datetime.datetime.now()
        print(endtime)
        conn = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        curs = conn.cursor()
        sql = "insert into user_log(id, starttime, endtime) values(%s, %s, %s)"
        curs.execute(sql, (USERID, starttime, endtime))
        print("log success!!!!")
        conn.commit()
        conn.close()
        #(수정2)
        self.kewordOfData(endtime)
        self.visitURLOfData(endtime)

        s_socket.close() #소켓종료 > 나중에 제대로 고치기
        qApp.quit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    myWindow = MainWindow()
    myWindow.show()
    app.exec_()
