from socket import *
import socket
import threading
import socketserver

th = []
pc = None
phone = []

server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_socket.bind(("",5001))
server_socket.listen(1)

def phone_client(conn,addr,data):
    #나중에 pc-phone 일치하는지 검사부분 추가하기 (휴대폰번호이용)
    global pc
    if pc is not None:
    	pc.sendall(data.encode('utf-8'))

def pc_client(conn,addr):
    #data가져오고, 얼굴인식하는 소스 넣기
    print('피시접속')
    
print("TCPServer Waiting for client on port 5001")

while True:
    client_socket, addr = server_socket.accept()
    data = client_socket.recv(65535).decode().strip()

    print(data)
    if data == 'pc':
        pc = client_socket
        client = threading.Thread(target=pc_client,args=(client_socket,addr))
    else :
        phone.append(client_socket)
        #pc.sendall(data.encode('utf-8'))
        client = threading.Thread(target=phone_client,args=(client_socket,addr,data))
    client.start()
    th.append(client)
    for t in th:
        t.join()
