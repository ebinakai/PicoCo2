from machine import Pin, I2C, reset
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
        self.is_show = True
        self.lines = ['', '', '', '']   # 固定の4行を初期化
        self.x = [0, 0, 0, 0]           # 各行のx座標
        self.y = [4, 20, 36, 52]        # 各行のy座標

    def set_line(self, line_number, text, x):
        if 0 <= line_number < 4:
            self.lines[line_number] = text
            self.x[line_number] = x

    def show(self):
        self.display.fill(0)
        
        if not self.is_show:
            self.display.show()
            return
        
        # 横線を描画
        self.display.hline(0, 16, 128, True)
        self.display.hline(0, 32, 128, True)
        self.display.hline(0, 48, 128, True)
        
        # テキストを表示
        for i, text in enumerate(self.lines):
            self.display.text(text, self.x[i], self.y[i], True)

        self.display.show()
        
    def set_is_show(self, is_show):
        self.is_show = is_show
        self.show()
        
    def get_is_show(self):
        return self.is_show

# Wifiに接続
def connect_wlan():
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
        
    return wlan

# NTPサーバーから時刻を取得
def sync_ntp(retry=3):
    attempt = 0
    while attempt < retry:
        try:
            dm.set_line(2, 'Syncing clock..', 4)
            dm.show()
            ntptime.settime()
            return True
        except Exception as e:
            dm.set_line(2, 'Retrying...', 4)
            dm.show()
            attempt += 1
            sleep(1)
    raise Exception('Failed to sync clock')

# APIにデータを送信
def send_post():
    # データをJSON形式で送信
    data = [
        {'name': 'co2', 'value': sensor.ppm},
        {'name': 'temp', 'value': sensor.temp}
    ]
    
    try:
        response = urequests.post(API_URL, json=data)
    except Exception as e:  
        return 'Network Error..'

    if response.status_code == 201: # 応答の確認
        json = response.json()
        message = json.get('message', 'success')
    else:
        message =  f'Failed: {response.status_code}'

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
UART_ID        = const(1)       # UART ID
I2C_ID         = const(0)       # I2C ID
I2C_FREQ       = const(400_000) # I2C バス速度
OLED_WIDTH     = const(128)     # OLEDの横ドット数
OLED_HEIGHT    = const(64)      # OLEDの縦ドット数
OLED_ADDR      = const(0x3c)    # OLEDのI2Cアドレス
OLED_SCL       = const(17)      # OLEDのSCLピン
OLED_SDA       = const(16)      # OLEDのSDAピン
SEND_EVERY_SEC = const(300)     # 何秒間隔でデータを送信するか
EXIT_TRY       = const(2)       # プログラム終了までの猶予(0までカウントされる)
is_sleep = False

# LEDを有効化
pin = Pin('LED', Pin.OUT)

# GPIO 21を入力として設定し、内蔵のプルダウン抵抗を無効にする
button = Pin(21, Pin.IN, Pin.PULL_UP)
# 割り込みハンドラ関数 - ディスプレイの表示・非表示を切り替え
def handle_interrupt(pin):
    if is_sleep:
        return
    dm.set_is_show(not dm.get_is_show())
button.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)

# MH-Z19センサーを有効化
sensor = mhz19.mhz19(UART_ID)

# OLEDを有効化
is_display = True
i2c = I2C(I2C_ID, sda=Pin(OLED_SDA), scl=Pin(OLED_SCL), freq=I2C_FREQ)
display = ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
dm = DisplayManager(display)

try :
    # Wifiを有効化
    wlan = connect_wlan()

    # IPアドレスを取得
    print('Network config:', wlan.ifconfig())
    ipaddress = wlan.ifconfig()[0]

    # 接続状態とIPアドレスを表示
    dm.set_line(0, ipaddress, 8)
    dm.set_line(1, 'Connected!', 4)
    dm.show()

    # NTPサーバーから時刻を取得し、RTCに設定
    sync_ntp()

    # NTP時刻取得完了メッセージ
    dm.set_line(2, 'Clock synced!', 4)
    dm.set_line(3, 'Booting up...', 4)
    dm.show()
    
except Exception as e:
    dm.set_line(2, 'Error occurred,', 4)
    dm.set_line(3, 'Restarting...', 4)
    sleep(1)
    reset()

# loop forever
dm.set_line(3, 'Booted!!', 4)
dm.show()
exit_count = 0
while True:
    sleep(0.8)
    
    # ボタンの長押しでスリープ及び解除
    if rp2.bootsel_button():
        # スリープ状態の場合、スリープを解除
        if is_sleep:
            if exit_count > EXIT_TRY:
                exit_count = 0
                is_sleep = False
                dm.set_line(1, 'Waking up...', 4)
                dm.set_is_show(True)
            else :
                exit_count += 1
                pin.toggle()
                continue
            
        # 非スリープ状態の場合はスリープに以降
        else:
            if exit_count > EXIT_TRY:
                dm.set_is_show(False)
                pin.off()
                is_sleep = True
                continue
            else :
                #  スリープまでのカウントダウン
                dm.set_is_show(True)
                dm.set_line(1, str(EXIT_TRY - exit_count) + ' to sleep', 4)
                exit_count += 1

    # ボタンが押されていない場合、カウントをリセット
    else:
        exit_count = 0
        if is_sleep:
            continue
    
        # 現在時刻を取得
        hour, minute, second = get_jst()
        str_jst = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)
        dm.set_line(1, 'Now : ' + str_jst, 4)
    
    # CO2センサーからデータを取得
    try :
        sensor.get_data()
        dm.set_line(2, 'Temp: ' + str(sensor.temp) + 'C', 4)
    except Exception as e:
        dm.set_line(1, 'CO2/temp sensor', 4)
        dm.set_line(2, 'read fail..', 4)

    # 指定された頻度でデータベースに値を送信
    if (minute * 60 + second) % SEND_EVERY_SEC == 0:
        response = send_post()
        dm.set_line(3, response, 4)
        print(response)
    else :
        dm.set_line(3, 'CO2 : ' + str(sensor.ppm) + 'ppm', 4)

    # 設定した表示を反映
    dm.show()
    
    # LED点滅
    if dm.get_is_show():
        pin.toggle()
    else :
        pin.on()
