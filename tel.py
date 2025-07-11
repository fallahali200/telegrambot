from flask import Flask, request, jsonify, send_from_directory
import telebot
import threading
import requests
import sqlite3
import os
import json
from uuid import uuid4
import random
import string
import qrcode
from io import BytesIO
import time as time_module
import time

# ---------- تنظیمات اولیه ----------
panel = 'https://start.myspeedhost.xyz:2040/yERnfjtsR1YckMR/'
login_url = panel + 'login'
list_inbound=panel+'panel/inbound/list'
add_inbound = panel + 'panel/inbound/add'
add_client=panel+'panel/inbound/addClient'
delete_client=panel+'panel/inbound/'
update_client=panel+'panel/inbound/updateClient/'
delete_inbound=panel+'/panel/inbound/del/'
server_address = "start.myspeedhost.xyz"
username = "admin"
password = "admin"

data = {
    'username': username,
    'password': password
}

session = requests.session()
alpha = session.post(url=login_url, json=data, timeout=5)
# ---------- تنظیمات ربات ----------
API_TOKEN = "7677315045:AAGINbVxwHxHQsooGFMoMS4qyF-mk1KyvPA"
bot = telebot.TeleBot(API_TOKEN)

# ---------- تنظیمات Flask ----------
app = Flask(__name__)
PRICE_PER_GB = 5000  # تومان

# ---------- اتصال به SQLite ----------
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    # جدول کاربران
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            balance INTEGER NOT NULL
        )
    ''')

    # جدول سرویس‌ها - چندتا سرویس می‌تونه برای یک کاربر وجود داشته باشه
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            subid TEXT NOT NULL,
            config_status INTEGER NOT NULL DEFAULT 1,
            time INTEGER,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')

    # افزودن کاربر اولیه
    conn.commit()
    conn.close()


def add_user(username, balance=100000):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO users (username, balance) VALUES (?, ?)", (username, balance))
        conn.commit()
        print(f"User {username} added successfully (or already existed).")
    finally:
        conn.close()


def get_balance(username):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT balance FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def update_balance(username, new_balance):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("UPDATE users SET balance = ? WHERE username = ?", (new_balance, username))
    conn.commit()
    conn.close()
    
    
def random_string(length):
    chars = string.ascii_lowercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))
   
   
   
def gb_to_bytes(gb_value):
    """تبدیل گیگابایت به بایت"""
    return int(gb_value * (1024 ** 3))  
 
def bytes_to_gigabytes(bytes_value):
    return round(bytes_value / (1024 ** 3), 2)  # بر حسب گیگابایت با دقت دو رقم اعشار
   
def send_qrcode(text, user_id, title=""):
    # ساخت QR کد
    qr = qrcode.QRCode(version=1, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')

    # تبدیل به بایت
    bio = BytesIO()
    bio.name = 'qr.png'
    img.save(bio, 'PNG')
    bio.seek(0)

    # ارسال عکس QR با کپشن عنوان و ذخیره پیام
    photo_message = bot.send_photo(user_id, bio, caption=title)

    # ارسال لینک با ایموجی 👇 و گرفتن message_id پیام ارسالی
    text_message = bot.send_message(user_id, text)

    # تابع حذف پیام‌ها بعد ۱۰ دقیقه
    def delete_later():
        time.sleep(600)  # 10 دقیقه
        try:
            bot.delete_message(user_id, photo_message.message_id)
        except Exception as e:
            print(f"خطا در حذف پیام عکس: {e}")

        try:
            bot.delete_message(user_id, text_message.message_id)
        except Exception as e:
            print(f"خطا در حذف پیام متن: {e}")

    # اجرای حذف پیام‌ها در یک Thread جدا
    threading.Thread(target=delete_later).start()

    
    
    
def generate_vless_link(client_id,server_address, port, remark, email):
    """تولید لینک VLESS"""
    return f"vless://{client_id}@{server_address}:{port}?type=tcp&security=none#{remark}-{email}"




def insert_sql(username, subid, config_status=1, timestamp=None):
    if timestamp is None:
        timestamp = int(time_module.time())  # ذخیره زمان فعلی

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        INSERT INTO services (username, subid, config_status, time)
        VALUES (?, ?, ?, ?)
    ''', (username, subid, config_status, timestamp))

    conn.commit()
    conn.close()




def delete_sql(username, subid):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        DELETE FROM services
        WHERE username = ? AND subid = ?
    ''', (username, subid))

    conn.commit()
    conn.close()




def update_sql(config_status, timestamp, username, subid):

    conn = sqlite3.connect('users.db')
    c = conn.cursor()

    c.execute('''
        UPDATE services
        SET config_status = ?, time = ?
        WHERE username = ? AND subid = ?
    ''', (config_status, timestamp, username, subid))

    conn.commit()
    conn.close()


def get_expiry_timestamp(days):
    now = int(time.time() * 1000)  # زمان فعلی به میلی ثانیه
    expiry = now + (days * 24 * 60 * 60 * 1000  )
    return expiry

def get_all_times(username, subid):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT time FROM services WHERE username = ? AND subid = ?", (username, str(subid)))
    times = [row[0] for row in c.fetchall()]
    conn.close()
    return times



def generate_safe_port():
    excluded_ports = {80, 443, 22, 3306, 5432, 8080, 8443, 5000, 6379}
    while True:
        port = random.randint(49152, 65535)
        if port not in excluded_ports:
            return port




def add_commas(number):
    return "{:,}".format(number)


init_db()

# ---------- روت‌های Flask ----------
@app.route('/add.html')
def index():
    return send_from_directory('.', 'add.html')

@app.route('/list.html')
def serve_list():
    return send_from_directory('.', 'list.html')

@app.route('/update.html')
def serve_list2():
    return send_from_directory('.', 'update.html')


@app.route('/update.html')
def update():
    id = request.args.get('id')
    print(f"Visited update.html with id = {id}")
    return send_from_directory('update.html')




@app.route('/check_capacity')
def check_capacity():
    current_users = 90
    max_users = 100
    return jsonify({'has_capacity': current_users < max_users})

@app.route('/get_balance')
def get_balance_route():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'balance': 0})
    balance = get_balance(user_id)
    return jsonify({'balance': balance})


@app.route('/list_users')
def list_users():
    user_id = request.args.get('user_id')

    # --- گرفتن موجودی کاربر ---
    balance = get_balance(user_id)

    # --- گرفتن لیست سرویس‌ها ---
    alpha = session.post(url=list_inbound)
    list_data = alpha.json()

    if not list_data.get("success"):
        return jsonify({
            'clients': [],
            'balance': balance
        }), 200

    inbounds = list_data.get("obj", [])
    inbound_match = next((i for i in inbounds if i.get("remark") == user_id), None)

    if not inbound_match:
        return jsonify({
            'clients': [],
            'balance': balance
        }), 200

    inbound_id = inbound_match.get("id")

    # --- دوباره گرفتن داده‌ها برای استخراج دقیق‌تر کلاینت‌ها ---
    alpha = session.post(url=list_inbound)
    list_data = alpha.json()
    inbounds = list_data.get("obj", []) if list_data.get("success") else []

    client_configs = []

    for inbound in inbounds:
        if inbound.get("id") == inbound_id:
            clients = inbound.get('clientStats', [])
            settings = json.loads(inbound.get('settings', '{}'))
            for client in clients:
                client_info = next(
                    (c for c in settings.get('clients', []) if c.get('email') == client.get('email')), {}
                )
                try:
                 mytime_values = get_all_times(user_id)
                 mytime = mytime_values[0] if mytime_values else 'N/A'
                except Exception as e:
                 mytime = f'error:{str(e)}'
                client_config = {
                'id': client.get('id'),
                'inboundId': client.get('inboundId'),
                'enable': client.get('enable'),
                'email': client.get('email'),
                'up': client.get('up'),
                'down': client.get('down'),
                'expiryTime': client.get('expiryTime'),
                'total': client.get('total'),
                'reset': client_info.get('reset', 'N/A'),
                'uuid': client_info.get('id', 'N/A'),
                'totalGB': client_info.get('totalGB', 'N/A'),
                'flow': client_info.get('flow', 'N/A'),
                'limitip': client_info.get('limitIp', 'N/A'),
                'tgld': client_info.get('tgId', 'N/A'),
                'subId': client_info.get('subId', 'N/A'),
                'comment': client_info.get('comment', 'N/A'),
                'port':inbound['port'],
                'mytime': get_all_times(user_id,client_info.get('subId', 'N/A'))
                }
                client_configs.append(client_config)
                reversed_list = client_configs[::-1]
                # print(reversed_list)

    return jsonify({
        'clients': reversed_list,
        'balance': balance
    }), 200



@app.route('/show_services', methods=['POST'])
def show_services():
    data = request.get_json()
    # استخراج داده‌ها
    services = data.get('service')
    user_id = data.get('user_id')
    subscription_link = "https://start.myspeedhost.xyz:2050/subs/"    #####################################
    subscription_link=subscription_link+services['subId']
    send_qrcode(subscription_link, user_id, title="لینک ساب 👇")
    vless_link=generate_vless_link(services["uuid"],server_address,services['port'],user_id,services['email'])
    send_qrcode(vless_link, user_id, title="لینک VLESS 👇")

    return jsonify({
    'status': 'success',
    'close_app': True
        })
 

     
@app.route('/delete_service', methods=['POST'])
def delete_service():
    data = request.get_json()
    services = data.get('service')
    user_id = data.get('user_id')
    balance = get_balance(user_id)
    subid_delete=services['uuid']
    inbound_id=str(services['inboundId'])
    subId=services['subId']
    full_delete_url=delete_client+inbound_id+'/delClient/'+subid_delete
    alpha = session.post(url=full_delete_url)
    used_volume=services['up']+services['down']
    total_volume=services['total']
    net_volume=bytes_to_gigabytes(total_volume-used_volume)
    alpha_status = json.loads(alpha.text)
    if alpha_status.get('success') is True:
     print('ok1')
     delete_sql(user_id,subId)
     return_money=net_volume*PRICE_PER_GB
     update_balance(user_id, balance + return_money)
     balance = get_balance(user_id)
     return jsonify({
     'message': f'مبلغ {return_money} تومان به حساب شما اضافه شد ✅',
     'Status': 'success',
     'balance':  balance
     }), 200
    else:
     alpha = session.post(url=f'https://start.myspeedhost.xyz:2040/yERnfjtsR1YckMR/panel/inbound/del/{inbound_id}', json=data)
     alpha_status = json.loads(alpha.text)
     print( alpha_status.get('success'))
     alpha_status = json.loads(alpha.text)
     if alpha_status.get('success') is True:
      delete_sql(user_id,subId)
      return_money=net_volume*PRICE_PER_GB
      update_balance(user_id, balance + return_money)
      balance = get_balance(user_id)
      return jsonify({
      'message': f'مبلغ {return_money} تومان به حساب شما اضافه شد ✅',
      'Status': 'success',
      'balance':  balance
      }), 200       





# @app.route('/toggle_service', methods=['POST'])
# def toggle_service():
#     data = request.get_json()
#     status=data["want_to_disable"][0]['enable']
#     if status==True:
#         subid_status = str(data['want_to_disable'][0]['uuid'])

#         full_status_url = staus_client + subid_status

#         settings = {
#             "clients": [{
#                 "id": str(data['want_to_disable'][0]['uuid']),
#                 "flow": str(data['want_to_disable'][0]['flow']),
#                 "email": str(data['want_to_disable'][0]['email']),
#                 "limitip": data['want_to_disable'][0]['limitip'],
#                 "totalGB": data['want_to_disable'][0]['totalGB'],
#                 "expiryTime": data['want_to_disable'][0]['expiryTime'],  # ← این خط جدید
#                 "enable": False,
#                 "tgld": str(data['want_to_disable'][0]['tgld']),
#                 "comment": str(data['want_to_disable'][0]['comment']),
#                 "rest": data['want_to_disable'][0]['reset']
#             }]
#         }

#         json_payload = {
#             "id": data['want_to_disable'][0]['inboundId'],
#             "settings": json.dumps(settings)
#         }

#         alpha = session.post(url=full_status_url,json=json_payload)
#         return jsonify({
#         'message': '✅ کانفیگ با موفقیت  فعال شد',
#         'clients': '1',
#         'balance':  '2'
#         }), 200 
#     else:  
        
#         subid_status = str(data['want_to_disable'][0]['uuid'])
#         print(data['want_to_disable'][0]['inboundId'])

#         full_status_url = staus_client + subid_status

#         settings = {
#             "clients": [{
#                 "id": str(data['want_to_disable'][0]['uuid']),
#                 "flow": str(data['want_to_disable'][0]['flow']),
#                 "email": str(data['want_to_disable'][0]['email']),
#                 "limitip": data['want_to_disable'][0]['limitip'],
#                 "totalGB": data['want_to_disable'][0]['totalGB'],
#                 "expiryTime": data['want_to_disable'][0]['expiryTime'],  # ← این خط جدید
#                 "enable":True,
#                 "tgld": str(data['want_to_disable'][0]['tgld']),
#                 "comment": str(data['want_to_disable'][0]['comment']),
#                 "rest": data['want_to_disable'][0]['reset']
#             }]
#         }

#         json_payload = {
#             "id": data['want_to_disable'][0]['inboundId'],
#             "settings": json.dumps(settings)
#         }

#         alpha = session.post(url=full_status_url,json=json_payload)        
#         return jsonify({
#         'message': '✅ کانفیگ با موفقیت  فعال شد',
#         'clients': '1',
#         'balance':  '2'
#         }), 200 


@app.route('/create_user', methods=['POST'])
def create_user():
    data = request.json
    username = data.get('username')
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    user_id = data.get('user_id')
    price = volume * PRICE_PER_GB

    balance = get_balance(user_id)
    if balance < price:
        return jsonify({'message': '❌ موجودی کافی نیست'}), 403

    else:
     alpha = session.post(url=list_inbound)
     list_data=alpha.json()
     if list_data.get("success"):
      inbounds = list_data.get("obj", [])
      inbound_match = None
      port_match=None
      for inbound in inbounds:
          if inbound.get("remark") == user_id:
              inbound_match = inbound
              port_match = inbound.get("port")  # ✅ استخراج مقدار پورت
              break
      
      if inbound_match:
          inbound_id = inbound_match.get("id")
          print(inbound_id)
          port_client=port_match
          random_email_client=random_string(5)
          clientid_inblound=str(uuid4())
          random_subid_client=random_string(8)
          add_client_data={
           
           
             "id": inbound_id,
             "settings": json.dumps(
             {
                 "clients": [{
                     "id": clientid_inblound,
                     "flow": "",
                     "email": username+random_email_client,
                     "limitIp": 0,
                     "totalGB": gb_to_bytes(volume),
                     "expiryTime": (-86400000*expire),
                     "enable": True,
                     "tgId": "",
                     "subId": random_subid_client,
                     "comment": username,
                     "reset": 0
                 }]
             }
             )

          }
          alpha = session.post(url=add_client,json=add_client_data)
          alpha_status = json.loads(alpha.text)
          if alpha_status.get('success') is True:
           insert_sql(user_id,random_subid_client,'1',get_expiry_timestamp(expire))
           subscription_link = "https://start.myspeedhost.xyz:2050/subs/"    #####################################
           subscription_link=subscription_link+random_subid_client
           send_qrcode(subscription_link, user_id, title="لینک ساب 👇")
           vless_link=generate_vless_link(clientid_inblound,server_address,port_client,user_id,username+random_email_client)
           send_qrcode(vless_link, user_id, title="لینک VLESS 👇")
           update_balance(user_id, balance - price)
           balance = get_balance(user_id)
           return jsonify({
             'message': f'\u200Eکانفیگ با موفقیت ساخته شد و مبلغ {add_commas(price)} تومان از حساب شما کسر شد ✅',
             'balance':  balance,
             'close_app': True 
        }), 200 
          #################add_inblound
      else:
       print(1)   
       clientid_inblound=str(uuid4())
       random_port_inbound = generate_safe_port()
       random_email_inbound=random_string(5)#we can just edit this
       random_subid_inbound=random_string(8)
       add_inbound_data = {
           "up": 0,
           "down": 0,
           "total": 0,
           "remark": user_id,
           "enable": True,
           "expiryTime": 0,
           "listen": "",
           "port": random_port_inbound,
           "protocol": "vless",
           "settings": json.dumps({
               "clients": [
                   {
                       "id": clientid_inblound,
                       "flow": "",
                       "email": username+random_email_inbound,
                       "limitIp": 0,
                       "totalGB": gb_to_bytes(volume),
                       "expiryTime": (-86400000*expire),
                       "enable": True,
                       "tgId": "",
                       "subId": random_subid_inbound,
                       "comment": username,
                       "reset": 0
                   }
               ],
               "decryption": "none",
               "fallbacks": []
           }),
           "streamSettings": json.dumps({
               "network": "tcp",
               "security": "none",
               "externalProxy": [],
               "tcpSettings": {
                   "acceptProxyProtocol": False,
                   "header": {
                       "type": "none"
                   }
               }
           }),
           "sniffing": json.dumps({
               "enabled": False,
               "destOverride": ["http", "tls", "quic", "fakedns"],
               "metadataOnly": False,
               "routeOnly": False
           }),
           "allocate": json.dumps({
               "strategy": "always",
               "refresh": 5,
               "concurrency": 3
           })
       }
       alpha = session.post(url=add_inbound,json=add_inbound_data)
       alpha_status = json.loads(alpha.text)
       if alpha_status.get('success') is True:
        alpha_status.get('success')
        print(1)   
        insert_sql(user_id,random_subid_inbound,'1',get_expiry_timestamp(expire)) 
        subscription_link = "https://start.myspeedhost.xyz:2050/subs/" #####################################
        subscription_link=subscription_link+random_subid_inbound
        send_qrcode(subscription_link, user_id, title="لینک ساب 👇")
        vless_link=generate_vless_link(clientid_inblound,server_address,random_port_inbound,user_id,username+random_email_inbound)
        send_qrcode(vless_link, user_id, title="لینک VLESS 👇")
        update_balance(user_id, balance - price)
        balance = get_balance(user_id)
        return jsonify({
            'message': f'\u200Eکانفیگ با موفقیت ساخته شد و مبلغ {add_commas(price)} تومان از حساب شما کسر شد ✅',
            'balance':  balance,
            'close_app': True 
        }), 200
     else:
      print("⛔️ خطا در گرفتن لیست inbounds:", data.get("msg"))
 
 
 
 
@app.route('/update_user', methods=['POST'])
def update_user():
 
    data = request.json
    # print(data)
    username = data.get('username')
    expire = int(data.get('expire'))
    volume = int(data.get('volume'))
    price = volume * PRICE_PER_GB
    user_id = data.get('user_id')
    balance = get_balance(user_id)
    if balance < price:
     return jsonify({'message': '❌ موجودی کافی نیست'}), 403
    else:
     uuid=data['service']['uuid']
     id = data['service']['inboundId']
     flow=data['service']['flow']
     email=data['service']['email']
     limitip=data['service']['limitip']
     totalGB=data['service']['totalGB']
     expiryTime=data['service']['totalGB']
     enable=data['service']['enable']
     tgld=data['service']['tgld']
     subId=data['service']['subId']
     comment=data['service']['comment']
     reset=data['service']['reset']
     full_status_url = update_client + uuid
     settings = {
         "clients": [{
             "id": subId,
             "flow": flow,
             "email": email,
             "limitip": limitip,
             "totalGB":gb_to_bytes(volume),
             "expiryTime":(-86400000*expire),
             "enable": enable,
             "tgld": tgld,
             "subId": subId,
             "comment": comment,
             "reset": reset
         }]
     }
     json_payload = {
         "id": id,
         "settings": json.dumps(settings)
     }
     used_volume=data['service']['up']+data['service']['down']
     total_volume=data['service']['total']
     remaining_volume_volume=bytes_to_gigabytes(total_volume-used_volume)
     volume_for_new=remaining_volume_volume - volume
     price=int(volume_for_new*PRICE_PER_GB)
     update_balance(user_id, balance + price)
     balance = get_balance(user_id)
     alpha = session.post(url=full_status_url,json=json_payload)
     alpha_status = json.loads(alpha.text)
     if alpha_status.get('success') is True:
      update_sql('1',get_expiry_timestamp(expire),user_id,subId)
      if price<0:
        abs_price=add_commas(abs(price))
        return jsonify({
        'message': f'\u200Eکانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان از حساب شما کسر شد ✅',
        'balance':  balance,
        'close_app': True 
        }), 200
 
      if price == 0 :
       abs_price=add_commas(abs(price))
       return jsonify({
       'message': f'زمان کانفیگ شما با موفقیت تمدید شد ✅',
       'balance':  balance,
       'close_app': True 
       }), 200

      else:
       abs_price=add_commas(abs(price))   
       return jsonify({
      'message': f'\u200Eکانفیگ با موفقیت تمدید شد و مبلغ {abs_price} تومان به حساب شما اضافه شد ✅',
      'balance':  balance,
      'close_app': True 
      }), 200
  
 

      
# ---------- ربات تلگرام ----------
@bot.message_handler(commands=['start'])
def send_welcome(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1)
    btn = telebot.types.KeyboardButton('ساخت کانفیگ')
    keyboard.add(btn)
    bot.send_message(
        message.chat.id,
        "سلام! برای ساخت کانفیگ دکمه زیر رو بزن.",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: message.text == "ساخت کانفیگ")
def open_mini_app(message):
    user_id = message.from_user.id

    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=1)

    webapp_btn1 = telebot.types.KeyboardButton(
        'باز کردن مینی اپ',
        web_app=telebot.types.WebAppInfo(url=f"https://tradeshop.sbs/add.html?user_id={user_id}")
    )
    webapp_btn2 = telebot.types.KeyboardButton(
        'لیست کاربرها',
        web_app=telebot.types.WebAppInfo(url=f"https://tradeshop.sbs/list.html?user_id={user_id}",)
    )
    add_user(user_id)

    keyboard.add(webapp_btn1, webapp_btn2)

    bot.send_message(
        message.chat.id,
        "سلام! برای ساخت کانفیگ یا دیدن لیست کاربرها، یکی از دکمه‌ها را انتخاب کن.",
        reply_markup=keyboard
    )




# ---------- اجرای برنامه ----------z
def run_flask():
    app.run(port=5000, debug=False)

def run_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    threading.Thread(target=run_flask).start()
    threading.Thread(target=run_bot).start()
