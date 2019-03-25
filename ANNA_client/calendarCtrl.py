from __future__ import print_function
from datetime import datetime
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
from PyQt5.QtWidgets import *
from PyQt5 import uic
from PyQt5.QtCore import QDateTime

form_cal = uic.loadUiType("UI\\addSchedule.ui")[0]
class CalendarWindow(QDialog, form_cal):
    user = None
    def __init__(self,USERID):
        super().__init__()
        self.user = USERID
        self.setupUi(self)
        self.setWindowTitle("ANNA")
        self.edit_startTime.setDateTime(QDateTime.currentDateTime())
        self.edit_endTime.setDateTime(QDateTime.currentDateTime())

    def add(self):
        self.data = []
        #추가할 내용 가져오기
        #제목
        self.data.append(self.edit_title.text())

        #시작,종료일(RFC3339형식으로 변환)
        startT = self.edit_startTime.dateTime().toPyDateTime()
        self.data.append(startT.isoformat())

        endT = self.edit_endTime.dateTime().toPyDateTime()
        self.data.append(endT.isoformat())

        #장소&내용
        self.data.append(self.edit_locate.text())
        self.data.append(self.edit_content.toPlainText())

        cal = Calendar(self.user)
        cal.addSchedule(self.data)
        self.hide()

class Calendar:
    # If modifying these scopes, delete the file token.json.
    SCOPES = 'https://www.googleapis.com/auth/calendar'

    def __init__(self,USERID):
        store = file.Storage('token_'+USERID+'.json')
        creds = store.get()
        if not creds or creds.invalid:
            #토큰 위치 입력
            flow = client.flow_from_clientsecrets('client_secret_745918444535-rodofvq8org9ahg0jfpg9esueu63n37b.apps.googleusercontent.com.json'
                                                    , self.SCOPES)
            creds = tools.run_flow(flow, store)
        self.service = build('calendar', 'v3', http=creds.authorize(Http()))

    #특정일 일정가져오기
    def getSchedule(self,date):
        startTime = datetime(date.year, date.month, date.day, 0, 0, 0).isoformat()+ '+09:00'
        finishTime = datetime(date.year, date.month, date.day, 23, 59, 59).isoformat()+ '+09:00'
        events_result = self.service.events().list(calendarId='primary', timeMin=startTime, timeMax=finishTime, singleEvents=True, orderBy='startTime').execute()
        events = events_result.get('items', [])

        result = ""
        if not events:
            return '일정이 없습니다.'
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            result = result +start+" "+event['summary']+"\n"
        return result

    #일정 추가하기
    def addSchedule(self,data):
        print(data[0]+"/"+data[1]+"/"+data[2]+"/"+data[3]+"/"+data[4]+"/")
        event = {
          'summary': data[0],
          'location': data[3],
          'description': data[4],
          'start': {
            'dateTime': data[1],
            'timeZone': 'Asia/Seoul',
          },
          'end': {
            'dateTime': data[2],
            'timeZone': 'Asia/Seoul',
          },
        }

        event = self.service.events().insert(calendarId='primary', body=event).execute()
        print ('Event created: %s' % (event.get('htmlLink')))
