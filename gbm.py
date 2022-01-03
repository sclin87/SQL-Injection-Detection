#!/usr/bin/env python3
from sklearn.ensemble import GradientBoostingClassifier
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import pickle
import logging
import socket
import os
import selectors
from functools import lru_cache

server_addr = '/uds_socket'
sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
sock.bind(server_addr)
sock.listen()
sock.setblocking(False)
logging.basicConfig(filename='./sqlfilter.log', level=logging.INFO)
sel = selectors.DefaultSelector()
sel.register(sock, selectors.EVENT_READ, data=None)

tfbin = pickle.load(open('tfidf', 'rb'))
clfbin = pickle.load(open('gbmclf', 'rb'))

def extractwhere(query):
  while True: 
    search_result = re.search("\"(?:[^\"\\\]|\\\.)*?\"|'(?:[^'\\\]|\\\.)*?'|\\bwhere\\b",query)
    if search_result == None:
      return ""
    elif search_result.group() == "where":
      return query[search_result.end():]
    else:
      query = query[search_result.end():]

def compare_two_constant(compare_op,a,b):
  if type(a)!=type(b):
    return ""
  truestatement = " compare_result_true "
  if compare_op == "<>":
    if a!= b:
      return truestatement
  elif compare_op == ">=":
    if a >= b:
      return truestatement
  elif compare_op == "<=":
    if a <= b:
      return truestatement
  elif compare_op == "=":
    if a == b:
      return truestatement
  elif compare_op == ">":
    if a > b:
      return truestatement
  elif compare_op == "<":
    if a < b:
      return truestatement
  else:
    return " compare_two_constant_error "
  return " compare_result_false "
  
re_dict = pickle.load(open('re_dict', 'rb'))
ptn = re_dict["ptn"]
decimal_num = re_dict["decimal_num"]
heximal_num = re_dict["heximal_num"]
binary_num = re_dict["binary_num"]
decimal_float = re_dict["decimal_float"]
dql = re_dict["dql"]
kw = re_dict["kw"]
#kw = re_dict["kw_mysql"]
kw_sleep = re_dict["kw_sleep"]
logical = re_dict["logical"]
id = re_dict["id"]
comment = re_dict["comment"]
comment_start = re_dict["comment_start"]
comment_end = re_dict["comment_end"]
logical_op = re_dict["logical_op"]
sql_comparison = re_dict["sql_comparison"]
comparison = re_dict["comparison"]
bitwise_operator = re_dict["bitwise_operator"]
operator = re_dict["operator"]
escape = re_dict["escape"]
bracket = re_dict["bracket"]
parenthesize = re_dict["parenthesize"]
comma = re_dict["comma"]
semicolon = re_dict["semicolon"]
point = re_dict["point"]
quote = re_dict["quote"]
wildcard = re_dict["wildcard"]
strliteral = re_dict["strliteral"]
backtick = re_dict["backtick"]
tnid = re_dict["tnid"]
newlinetok = re_dict["newlinetok"]

def tokenize_qry(qries):
  raw = list()
  for qry in qries:
    q = qry.lower()
    q = extractwhere(q)
    #q = q.replace("'", "\"")
    word_list = re.findall(ptn,q)
    new_str = str()
    constant_str = str()
    constant_num = 0.0
    compare_op = ""
    constant_distance = 2
    last_constant_type = ""
    last_token_comparison = False
    in_comment_sl = False
    in_comment_ml = False
    for x in word_list:
      last_token_comparison = False
      constant_distance += 1
      if in_comment_sl or in_comment_ml:
        if in_comment_sl:
          if re.match(newlinetok,x):
            in_comment_sl = False
          continue
        if in_comment_ml:
          if re.match(comment_end,x):
            in_comment_ml = False
          continue
      if re.match(binary_num,x):
        new_str += "binary_num"
        if compare_op == "":
          constant_num = float(int(x,2))
          last_constant_type = "num"
        elif last_constant_type == "num":
          new_str += compare_two_constant(compare_op,constant_num,float(int(x,2)))
        constant_distance = 0
      elif re.match(heximal_num, x):
        new_str += "heximal_num"
        if compare_op == "":
          constant_num = float(int(x,16))
          last_constant_type = "num"
        elif last_constant_type == "num":
          new_str += compare_two_constant(compare_op,constant_num,float(int(x,16)))
        constant_distance = 0
      elif re.match(decimal_float,x):
        new_str += "decimal_float"
        if compare_op == "":
          constant_num = float(x)
          last_constant_type = "num"
        elif last_constant_type == "num":
          new_str += compare_two_constant(compare_op,constant_num,float(x))
        constant_distance = 0
      elif re.match(decimal_num,x):
        new_str += "decimal_num"
        if compare_op == "":
          constant_num = float(int(x,10))
          last_constant_type = "num"
        elif last_constant_type == "num":
          new_str += compare_two_constant(compare_op,constant_num,float(int(x,10)))
        constant_distance = 0
      elif re.match(logical_op,x):
        new_str += re.match(logical_op,x).group(0)
      elif re.match(sql_comparison,x):
        new_str += "sql_comparison"
        if constant_distance == 1:
          last_token_comparison = True
          compare_op = x
      elif re.match(comparison,x):
        new_str += "comparison"
      elif re.match(strliteral,x):
        new_str += "strliteral"
        if compare_op == "":
          constant_str = x
          last_constant_type = "str"
        elif last_constant_type == "str":
          new_str += compare_two_constant(compare_op,constant_str,x)
        constant_distance = 0
      elif re.match(bitwise_operator,x):
        new_str += "bitwise_operator"
      elif re.match(dql,x):
        new_str += re.match(dql,x).group(0)
      elif re.match(tnid,x):
        new_str += "id"
      elif re.match(logical,x):
        #new_str += "logical"
        new_str += re.match(logical,x).group(0)
      elif re.match(backtick,x):
        new_str += "id"
      elif re.match(kw,x):
        new_str += "keyword"
      elif re.match(kw_sleep,x):
        new_str += "sleep"
      elif re.match(id,x):
        new_str += "id"
      elif re.match(comment,x):
        new_str += "comment"
        in_comment_sl = True
      elif re.match(comment_start,x):
        new_str += "comment"
        in_comment_ml = True
      elif re.match(operator,x):
        new_str += "operator"
      elif re.match(escape,x):
        new_str += "escape"
      elif re.match(bracket,x):
        new_str += "bracket"
      elif re.match(parenthesize,x):
        new_str += "parenthesize"
      elif re.match(comma,x):
        new_str += "comma"
      elif re.match(semicolon,x):
        new_str += "semicolon"
      elif re.match(point,x):
        new_str += "point"
      elif re.match(quote,x):
        new_str += "quote"
      elif re.match(wildcard,x):
        new_str += "wildcard"
      else:
        new_str += "others"
      new_str += " "
      if last_token_comparison != True:
        compare_op = ""
    raw.append(new_str)
  return raw

def _predict(s):
  ss = [s]
  qries = tokenize_qry(ss)
  if len(qries[0]) <= 1:
    return 0
  prediction = predict_cache(qries[0])
  return int(prediction.sum())

def predict(query):
    prediction = _predict(s=query)
    if prediction == 0:
        logging.info(query)
        return 0
    elif prediction == 1:
        logging.warning(query)
        return 1

#@lru_cache(maxsize=512)
def predict_cache(qries):
  qries = tfbin.transform([qries])
  return clfbin.predict(qries)

def serve(key, mask):
    sock = key.fileobj
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)
        if recv_data:
            query = recv_data.decode('ascii')
            ans = predict(query)
            sock.send(int(ans).to_bytes(2, 'little'))
        else:
            sel.unregister(sock)
            sock.close()


def accept_conn(lsock):
    conn, addr = lsock.accept()
    conn.setblocking(False)
    sel.register(conn, selectors.EVENT_READ, data=1)


while True:
    events = sel.select(timeout=10)
    for key, mask in events:
        if key.data == None:
            accept_conn(key.fileobj)
        else:
            serve(key, mask)
