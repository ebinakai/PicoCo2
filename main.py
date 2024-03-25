from machine import Pin, I2C, ADC, reset
from utime import sleep, localtime, mktime
import network
import ntptime
import ssd1306
import urequests
from env import WIFI_SSID, WIFI_PASSWORD, API_URL

# 定数
I2C_ID       = const(0)       # I2C ID
I2C_FREQ     = const(400_000) # I2C バス速度
OLED_WIDTH   = const(128)     # OLEDの横ドット数
OLED_HEIGHT  = const(64)      # OLEDの縦ドット数
OLED_ADDR    = const(0x3c)    # OLEDのI2Cアドレス
OLED_SCL     = const(17)      # OLEDのSCLピン
OLED_SDA     = const(16)      # OLEDのSDAピン
SEND_INTERVAL_SEC = const(60) # 送信間隔（秒）

# LED configuration
pin = Pin("LED", Pin.OUT)
pin.on()

# OLED configuration
# I2C設定 (I2C識別ID 0or1, SDA, SCL)
i2c = I2C(I2C_ID, sda=Pin(OLED_SDA), scl=Pin(OLED_SCL), freq=I2C_FREQ)
display = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
def display_clear():
    display.fill(0)
    display.hline(0, 12, 128, True)  # (x, y, 長さ, 色) 指定座標から横線
    display.hline(0, 32, 128, True)  # (x, y, 長さ, 色) 指定座標から横線

# ADC configuration
sensor_temp = ADC(4)
conversion_factor = 3.3 / (65535)

# Wi-Fi接続を試みる
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if not wlan.isconnected():
    print('Connecting to network...')
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    # 通信確立までの表示
    counter = 0
    dots = ["", ".", "..", "..."]
    while not wlan.isconnected():
        connect_message = 'Connecting' + dots[counter % len(dots)]
        display_clear()
        display.text(WIFI_SSID, 0, 2, True)  # ('内容', x, y, 色) テキスト表示
        display.text(connect_message, 10, 20, True)  # ('内容', x, y, 色) テキスト表示
        display.text('try: {}'.format(counter), 4, 40, True)  # ('内容', x, y, 色) テキスト表示
        display.text('Reboot if fail.', 4, 53, True)  # ('内容', x, y, 色) テキスト表示
        display.show()
        counter += 1
        pin.toggle()
        sleep(0.05)

# IPアドレスを取得
print('Network config:', wlan.ifconfig())
ipaddress = wlan.ifconfig()[0]

# 接続状態とIPアドレスを表示
display_clear()
display.text(ipaddress, 8, 2, True)
display.text('Connected!', 10, 20, True)
display.show()

# NTPサーバーから時刻を取得し、RTCに設定
ntptime.settime()

def get_temp():
    reading = sensor_temp.read_u16() * conversion_factor
    return round(27 - (reading - 0.706)/0.001721, 1)

def send_temp(value):
    # データをJSON形式で送信
    data = {'value': value}
    response = urequests.post(API_URL, json=data)

    # 応答の確認
    if response.status_code == 201:
        print('({}) Data sent successfully'.format(get_jst()))
        json = response.json()
        message = json.get('message', 'success')
    else:
        message =  'failed'

    # 接続のクローズ
    response.close()
    return message

def get_jst():
    # UTC時刻を取得
    utc_time = localtime()

    # JSTはUTC+9時間なので、秒単位で加算
    utc_timestamp = mktime(utc_time)
    jst_timestamp = utc_timestamp + 9 * 3600  # 9時間を秒単位で加算

    # タイムスタンプをローカルタイムに変換
    jst_time = localtime(jst_timestamp)
    
    # 時、分、秒を取得
    hour, minute, second = jst_time[3], jst_time[4], jst_time[5]

    return hour, minute, second

display.text('Project start!', 4, 40, True)  # ('内容', x, y, 色) テキスト表示
display.show()
while True:
    sleep(1)  # sleep
    
    # 基盤温度を取得
    temperature = get_temp()
    hour, minute, second = get_jst()
    str_jst = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)

    # 設定した内容を表示
    display_clear()
    display.text(ipaddress, 8, 2, True)  # ('内容', x, y, 色) テキスト表示
    display.text('Now : {}'.format(str_jst), 4, 20, True)  # ('内容', x, y, 色) テキスト表示
    display.text('Temp: {}C'.format(temperature), 4, 40, True)  # ('内容', x, y, 色) テキスト表示

    # 5分に一回の頻度で基板温度をデータベースに送信
    if minute % 5 == 0:
        try:
            send_temp(temperature)
            message = 'Data sent!'
        except Exception as e:
            message = 'Network Error...'
        finally:
            display.text(message, 4, 53, True)  # ('内容', x, y, 色) テキスト表示

    display.show()
    
    # LED点滅
    pin.toggle()