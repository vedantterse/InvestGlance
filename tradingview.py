from websocket import WebSocket, create_connection
import json
import pandas as pd 
socket_url="wss://data.tradingview.com/socket.io/websocket"
ws=create_connection(socket_url)
def create_msg(ws,fun , args):
    ms=json.dumps({"m":fun, "p":args})
    msg='~m~'+str(len(ms))+'~m~'+ms
    ws.send(msg)

create_msg(ws,"chart_create_session",["cs_e3vBkrz1qMJN",""] )
create_msg(ws,"resolve_symbol",["cs_TpDV914JscQX","sds_sym_1","={\"inputs\":{},\"symbol\":{\"adjustment\":\"splits\",\"session\":\"regular\",\"symbol\":\"NSE:NIFTY\"}"])
create_msg(ws,"create_series",["cs_TpDV914JscQX", "sds_1", "s1", "sds_sym_1", "1",10, ""])
while True:
    res=ws.recv()
    print(res)