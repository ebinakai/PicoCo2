from machine import Pin, I2C, ADC, reset
from utime import sleep, localtime, mktime
import network
import ntptime
import ssd1306
import mhz19
import urequests
from env import WIFI_SSID, WIFI_PASSWORD, API_URL

# OLEDに表示
class DisplayManager:
    def __init__(self, display):
        self.display = display
        self.lines = ['', '', '', '']   # 固定の4行を初期化
        self.x = [0, 0, 0, 0]           # 各行のx座標
        self.y = [4, 20, 36, 52]        # 各行のy座標

    def set_line(self, line_number, text, x):
        if 0 <= line_number < 4:
            self.lines[line_number] = text
            self.x[line_number] = x

    def show(self):
        self.display.fill(0)
        # 横線を描画
        self.display.hline(0, 16, 128, True)
        self.display.hline(0, 32, 128, True)
        self.display.hline(0, 48, 128, True)
        
        # テキストを表示
        for i, text in enumerate(self.lines):
            self.display.text(text, self.x[i], self.y[i], True)

        self.display.show()

# 基板温度を取得
def get_temp():
    reading = sensor_temp.read_u16() * CONVERSION_FACTOR
    return round(27 - (reading - 0.706)/0.001721, 1)

# APIにデータを送信
def send_post(value):
    # データをJSON形式で送信
    response = urequests.post(API_URL, json={'value': value})

    if response.status_code == 201: # 応答の確認
        json = response.json()
        message = json.get('message', 'success')
    else:
        message =  'failed'

    response.close()  # 接続のクローズ
    return message

# 現在時刻を取得
def get_jst():
    utc_time = localtime()                    # UTC時刻を取得
    utc_timestamp = mktime(utc_time)          # UTC時刻をタイムスタンプに変換
    jst_timestamp = utc_timestamp + 9 * 3600  # JSTはUTC+9時間なので、秒単位で加算
    jst_time = localtime(jst_timestamp)       # タイムスタンプをローカルタイムに変換
    hour, minute, second = jst_time[3:6]      # 時、分、秒のみを取得
    return hour, minute, second

# 定数
UART_ID           = const(1)       # UART ID
I2C_ID            = const(0)       # I2C ID
I2C_FREQ          = const(400_000) # I2C バス速度
OLED_WIDTH        = const(128)     # OLEDの横ドット数
OLED_HEIGHT       = const(64)      # OLEDの縦ドット数
OLED_ADDR         = const(0x3c)    # OLEDのI2Cアドレス
OLED_SCL          = const(17)      # OLEDのSCLピン
OLED_SDA          = const(16)      # OLEDのSDAピン
CONVERSION_FACTOR = 3.3 / (65535)  # ADC変換係数
SEND_EVERY_MIN    = const(5)       # 何分間隔でデータを送信するか

# LED configuration
pin = Pin('LED', Pin.OUT)
pin.on()

#init sensor on UART #1
sensor = mhz19.mhz19(UART_ID)

# OLEDを有効化
i2c = I2C(I2C_ID, sda=Pin(OLED_SDA), scl=Pin(OLED_SCL), freq=I2C_FREQ)
display = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
dm = DisplayManager(display)

# ADCを有効化
sensor_temp = ADC(4)  # ADC4ピンを使用

# Wifiを有効化
print('Connecting to network...')
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

# 通信確立までの表示
counter = 0
dots = ['', '.', '..', '...']
dm.set_line(0, WIFI_SSID, 0)
dm.set_line(3, 'Reboot if fail.', 4)
while not wlan.isconnected():
    connect_message2 = 'Connecting' + dots[counter % len(dots)]
    connect_message3 = 'try: ' + str(counter)
    dm.set_line(1, connect_message2, 4)
    dm.set_line(2, connect_message3, 4)
    dm.show()
    
    counter += 1
    pin.toggle()
    sleep(0.05)

# IPアドレスを取得
print('Network config:', wlan.ifconfig())
ipaddress = wlan.ifconfig()[0]

# 接続状態とIPアドレスを表示
dm.set_line(0, ipaddress, 8)
dm.set_line(1, 'Connected!', 4)
dm.set_line(2, 'Syncing clock..', 4)
dm.show()

# NTPサーバーから時刻を取得し、RTCに設定
ntptime.settime()

# NTP時刻取得完了メッセージ
dm.set_line(2, 'Clock synced!', 4)
dm.set_line(3, 'Booting up...', 4)
dm.show()

# loop
while True:
    sleep(1)  # sleep

    #update data from sensor
    sensor.get_data()
    print('ppm:',    sensor.ppm)
    print('temp:',   sensor.temp)
    print('status:', sensor.co2status)
    
    # 基盤温度を取得
    temperature = get_temp()
    hour, minute, second = get_jst()
    str_jst = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)

    # 設定した内容を表示
    dm.set_line(1, 'Now : ' + str_jst, 4)
    dm.set_line(2, 'Temp: ' + str(temperature) + 'C', 4)

    # 指定された頻度で基板温度をデータベースに送信
    if minute % SEND_EVERY_MIN == 0 and second == 0:
        try:
            send_post(temperature)
            dm.set_line(3, 'Data sent.', 4)
        except Exception as e:
            dm.set_line(3, 'Network Error...', 4)
    else :
        dm.set_line(3, 'Now is no then.', 4)

    # 設定した表示を反映
    dm.show()
    
    # LED点滅
    pin.toggle()
