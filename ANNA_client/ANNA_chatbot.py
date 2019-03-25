#!/usr/bin/env python

# Anna's Voice command processing file
# [START import_libraries]
from __future__ import division

import os
import re
import sys
import argparse
import uuid
import win32api
import webbrowser
import pyttsx3

import dialogflow
from google.cloud import speech
from google.cloud.speech import enums
from google.cloud.speech import types
import pyaudio
from six.moves import queue
from calendarCtrl import Calendar,CalendarWindow
from datetime import datetime
# [END import_libraries]

#오디오 관련 변수
RATE = 16000
CHUNK = int(RATE / 10)  # 100ms

#실행프로그램 관련 변수
notepad = "c:\windows\system32\\notepad.exe"
paint = "c:\windows\system32\\mspaint.exe"
kakao = "D:\program\Kakao\KakaoTalk\\KakaoTalk.exe"
#사이트 URL
naver ="https://search.naver.com/search.naver?query="
google ="https://www.google.co.kr/search?q="
youtube ="https://www.youtube.com/results?search_query="

class ANNA:
    window = None
    def __init__(self):
        print('챗봇 실행...')

    #프로그램 열어주는 함수들
    def openProgram(self,response):
        program = response.query_result.parameters['program']
        website = response.query_result.parameters['website']
        if program == '메모장':
            win32api.ShellExecute(0,'open',notepad,None,None,1)
        elif program == '그림판':
            win32api.ShellExecute(0,'open',paint,None,None,1)
        elif program == '카카오톡':
            win32api.ShellExecute(0,'open',kakao,None,None,1)

    #웹사이트 검색 함수
    def searchSite(self,response):
        website = response.query_result.parameters['website']
        searchWord = response.query_result.parameters['searchWord']
        global url
        if website=='구글' :
            url=google+searchWord
        elif website == '네이버' :
            url=naver+searchWord
        elif website == '유튜브' :
            url=youtube+searchWord
        webbrowser.open(url)

    #컴퓨터 종료 명령
    def shutdown(self,response):
        time = response.query_result.parameters['time']
        os.system("shutdown -s -t 0")

    #상세검색(길찾기, 식당찾기, 번역)
    def searchDetail(self,intent_kind,response):
        global url

        if intent_kind=="Command_Search_FindingWay" :
            departure = response.query_result.parameters['Departure']
            destination = response.query_result.parameters['Destination']
            url = "https://www.google.co.kr/maps/dir/"+departure+"/"+destination

        if intent_kind=="Command_Search_Restaurant" :
            locate = response.query_result.parameters['Area']
            url = "https://www.google.co.kr/search?q="+locate+"+맛집&tbm=lcl"

        if intent_kind=="Command_Search_Translation":
            sk = "auto"
            word = response.query_result.parameters['searchWord']
            tk = response.query_result.parameters['language']
            url = "https://papago.naver.com/?sk="+sk+"&tk="+tk+"&st="+word

        webbrowser.open(url)

    #오늘 일정 UI뜨게
    def getScheduleUI(self,response):
        self.window.calendarWidget.setSelectedDate(datetime.today().date())
        self.window.getSchedule()
        self.window.setTab(1)
        self.window.show()

    # [START dialogflow_detect_intent_text]
    def detect_intent_texts(self,project_id, session_id, text, language_code):
        session_client = dialogflow.SessionsClient()

        session = session_client.session_path(project_id, session_id)
        print('Session path: {}\n'.format(session))

        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)

        query_input = dialogflow.types.QueryInput(text=text_input)

        response = session_client.detect_intent(
            session=session, query_input=query_input)

        intent_kind = response.query_result.intent.display_name
        print('=' * 20)
        print('Query text: {}'.format(response.query_result.query_text))
        print('Detected intent: {} (confidence: {})\n'.format(
            response.query_result.intent.display_name,
            response.query_result.intent_detection_confidence))
        print('Fulfillment text: {}\n'.format(
            response.query_result.fulfillment_text))

        self.window.showTrayMessage(response.query_result.fulfillment_text)
        engine = pyttsx3.init()
        engine.say(response.query_result.fulfillment_text)
        engine.runAndWait()

        #나중에 webhook연결해서 좀 더 유동적인 대답 추가
        if intent_kind=="Command_OpenProgram" :
            self.openProgram(response)
        if intent_kind=="Command_Search" :
            self.searchSite(response)
        if intent_kind=="Command_ShutDown" :
            self.shutdown(response)
        if intent_kind=="Command_Search_FindingWay" or intent_kind=="Command_Search_Restaurant" or intent_kind=="Command_Search_Translation":
            self.searchDetail(intent_kind, response)
        if intent_kind=="Command_Schedule" :
            self.getScheduleUI(response)

    def listen_print_loop(self,responses):
        num_chars_printed = 0
        for response in responses:
            if not response.results:
                continue

            # The `results` list is consecutive. For streaming, we only care about
            # the first result being considered, since once it's `is_final`, it
            # moves on to considering the next utterance.
            result = response.results[0]
            if not result.alternatives:
                continue

            # Display the transcription of the top alternative.
            transcript = result.alternatives[0].transcript

            # Display interim results, but with a carriage return at the end of the
            # line, so subsequent lines will overwrite them.
            #
            # If the previous result was longer than this one, we need to print
            # some extra spaces to overwrite the previous result
            overwrite_chars = ' ' * (num_chars_printed - len(transcript))

            if not result.is_final:
                sys.stdout.write(transcript + overwrite_chars + '\r')
                sys.stdout.flush()

                num_chars_printed = len(transcript)

            else:
                print(transcript + overwrite_chars)
                # exit나 quit 인식 시 종료함
                if re.search(r'\b(exit|quit)\b', transcript, re.I):
                    print('Exiting..')
                    break

                #한마디만 하고 스피치 종료 시키기
                else :
                    self.detect_intent_texts("anna-test-87887",str(uuid.uuid4()),str(transcript + overwrite_chars),"ko")
                    print('Exiting..')
                    break

                num_chars_printed = 0

    def start(self,window):
        self.window = window
        language_code = 'ko-KR'  # a BCP-47 language tag

        client = speech.SpeechClient()
        config = types.RecognitionConfig(
            encoding=enums.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=RATE,
            language_code=language_code)
        streaming_config = types.StreamingRecognitionConfig(
            config=config,
            interim_results=True)

        #무한으로 하려면 'while True :'
        with MicrophoneStream(RATE, CHUNK) as stream:
            audio_generator = stream.generator()
            requests = (types.StreamingRecognizeRequest(audio_content=content)
                        for content in audio_generator)

            responses = client.streaming_recognize(streaming_config, requests)

            # Now, put the transcription responses to use.
            self.listen_print_loop(responses)

class MicrophoneStream(object):
    """Opens a recording stream as a generator yielding the audio chunks."""
    def __init__(self, rate, chunk):
        self._rate = rate
        self._chunk = chunk

        # Create a thread-safe buffer of audio data
        self._buff = queue.Queue()
        self.closed = True

    def __enter__(self):
        self._audio_interface = pyaudio.PyAudio()
        self._audio_stream = self._audio_interface.open(
            format=pyaudio.paInt16,
            # The API currently only supports 1-channel (mono) audio
            # https://goo.gl/z757pE
            channels=1, rate=self._rate,
            input=True, frames_per_buffer=self._chunk,
            # Run the audio stream asynchronously to fill the buffer object.
            # This is necessary so that the input device's buffer doesn't
            # overflow while the calling thread makes network requests, etc.
            stream_callback=self._fill_buffer,
        )

        self.closed = False

        return self

    def __exit__(self, type, value, traceback):
        self._audio_stream.stop_stream()
        self._audio_stream.close()
        self.closed = True
        # Signal the generator to terminate so that the client's
        # streaming_recognize method will not block the process termination.
        self._buff.put(None)
        self._audio_interface.terminate()

    def _fill_buffer(self, in_data, frame_count, time_info, status_flags):
        """Continuously collect data from the audio stream, into the buffer."""
        self._buff.put(in_data)
        return None, pyaudio.paContinue

    def generator(self):
        while not self.closed:
            # Use a blocking get() to ensure there's at least one chunk of
            # data, and stop iteration if the chunk is None, indicating the
            # end of the audio stream.
            chunk = self._buff.get()
            if chunk is None:
                return
            data = [chunk]

            # Now consume whatever other data's still buffered.
            while True:
                try:
                    chunk = self._buff.get(block=False)
                    if chunk is None:
                        return
                    data.append(chunk)
                except queue.Empty:
                    break

            yield b''.join(data)
