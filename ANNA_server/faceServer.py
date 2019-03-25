from socket import *
import socket
import os
import time
import sys
import base64
import pymysql
import requests

#사진 비교
def compare_face():
        con_mysql = pymysql.connect(db='user', host='18.220.43.141', user='root', passwd='hk1103', charset='utf8')
        cursor_mysql = con_mysql.cursor()
        cursor2 = con_mysql.cursor()

        #유저 사진 등록한 유저의 id와 image 가져옴
        sql = "select id, image from userDB where image is not null"
        cursor_mysql.execute(sql)
        image_list = cursor_mysql.fetchall()

        os.system('sudo docker start anna_docker')
        for image in image_list:
                cursor_mysql.execute('select server_chk from userDB where id = %s and server_chk = 1', (image[0],))
                check = cursor_mysql.fetchone()

                if check is None:
                        filename = 'face_' + image[0] + '.png'
                        f = open(filename, 'wb')
                        f.write(image[1])
                        f.close()

                        command = 'sudo docker cp ' +filename+ ' anna_docker:./'+filename
                        os.system(command)

                        #cursor2.execute('update userDB set server_chk = 1 where id = %s', (image[0],))
                        #con_mysql.commit()
                else:
                        continue
        os.system('sudo docker exec anna_docker python ./openface/demos/compare.py {face_*.png, registerImg.png} > result.txt')
        os.system('sudo docker stop anna_docker')
        os.system('rm -rf face_*.png')

        result_file = open('result.txt', 'r')
        line = result_file.readline()
        if line is not None:
                id = line.split(' ')[0].split('_')[1].split('.')[0]
                #compare_num = line.split(' ')[1].split()[0]
                return id

sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
sock.bind(("",5002))
sock.listen(5)
data_transferred = 0
while True:
	print("TCPServer Waiting for client on port 5002")
	client_socket, address = sock.accept()
	print("I got a connection from ", address)

	data=client_socket.recv(1024)
	if not data:
		print("파일 전송 중 오류발생")
	with open('registerImg.png','wb') as f:
		try:
			f.write(data)
			while True:
				print('recv..')
				data = client_socket.recv(1024)
				if 'finish' in str(data):
					print(str(data))
					f.write(data)
					print(str(data)[:-7])
					break
				f.write(data)
				data_transferred += len(data)
		except Exception as e:
			print(e)

	print('파일 전송종료. 전송량 [%d]' %(data_transferred))


	id = compare_face()
    buf = bytes(id,encoding='utf-8')
	client_socket.send(buf)
