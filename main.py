from machine import Pin, I2C, reset
from utime import sleep, localtime, mktime, ticks_ms, ticks_diff
import network
import ntptime
import ssd1306
import mhz19
import urequests
import rp2
from env import WIFI_SSID, WIFI_PASSWORD, API_URL

# MicroPythonではenumモジュールが利用できないため、クラス定数として定義
class DisplayMode:
    SLEEP = 1
    SETUP = 2
    RUNNING = 3

# OLEDに表示
class DisplayManager:
    def __init__(self, display: ssd1306.SSD1306_I2C_Extended):
        self.display = display
        self.is_show = True
        self.status = DisplayMode.SETUP
        self.line_objects = [{'text': '', 'x': 0, 'scale': 1} for _ in range(4)]  # オブジェクトの配列
        self.lines = [''] * 4      # 固定の4行を初期化
        self.x = [0] * 4           # 各行のx座標
        self.y4 = [4, 20, 36, 52]  # 各行のy座標
        self.y3 = [4, 25, 50]      # 3行目までのy座標
        self.scales = [1, 1, 1, 1] # 各行のスケール（拡大倍率）
        
    def set_line(self, line_number: int, text: str, x: int, scale: int=1):
        if 0 <= line_number < 4:
            # オブジェクトの配列で管理
            self.line_objects[line_number] = {
                'text': text,
                'x': x,
                'scale': scale
            }
            # 0 <= line_number < 4 の範囲であることを確認
            self.lines[line_number] = text
            self.x[line_number] = x
            self.scales[line_number] = scale

    def show(self):
        # ディスプレイをクリア
        self.display.fill(0)
        
        if self.status == DisplayMode.SLEEP:
            self.display.show()
            return
        
        if self.status == DisplayMode.SETUP:
            # 横線を描画
            self.display.hline(0, 16, 128, True)
            self.display.hline(0, 32, 128, True)
            self.display.hline(0, 48, 128, True)
            
            # テキストを表示
            for i in range(4):
                self.display.text(self.line_objects[i]['text'],
                                  self.line_objects[i]['x'], self.y4[i], True, 1)
                
        elif self.status == DisplayMode.RUNNING:
            # 横線を描画
            self.display.hline(0, 21, 128, True)
            self.display.hline(0, 42, 128, True)
            
            # テキストを表示
            for i in range(3):
                self.display.text(self.line_objects[i]['text'],
                                  self.line_objects[i]['x'], self.y3[i], True, 2)

        self.display.show()
        
    def set_status(self, status: DisplayMode):
        self.status = status
        self.show()
    
    def get_status(self):
        return self.status

# Wifiに接続
def connect_wlan(dm: DisplayManager):
    
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
        sleep(0.05)
        
    return wlan

# NTPサーバーから時刻を取得
def sync_ntp(dm: DisplayManager, retry=3):
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
def send_post(ppm=None, temp=None):
    if ppm is None or temp is None:
        return 'Invalid sensor data.'
    
    # データをJSON形式で送信
    data = [
        {'name': 'co2', 'value': ppm},
        {'name': 'temp', 'value': temp}
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

def setup():
    # LEDを有効化
    led = Pin('LED', Pin.OUT)

    # GPIO 21を入力として設定し、内蔵のプルダウン抵抗を無効にする
    button = Pin(21, Pin.IN, Pin.PULL_UP)
    # 割り込みハンドラ関数 - ディスプレイの表示・非表示を切り替え
    def handle_interrupt(pin):
        dm.set_status(DisplayMode.RUNNING if dm.get_status() == DisplayMode.SLEEP else DisplayMode.SLEEP)
        sleep(0.1)  # ボタンのチャタリング防止のために少し待機
    button.irq(trigger=Pin.IRQ_RISING, handler=handle_interrupt)

    # MH-Z19センサーを有効化
    sensor = mhz19.mhz19(UART_ID)
    
    # OLEDを有効化
    i2c = I2C(I2C_ID, sda=Pin(OLED_SDA), scl=Pin(OLED_SCL), freq=I2C_FREQ)
    display_ssd1306 = ssd1306.SSD1306_I2C_Extended(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
    dm = DisplayManager(display_ssd1306)
    
    try :
        # Wifiを有効化
        wlan = connect_wlan(dm)
        
        print('WLAN connected:', wlan.isconnected())

        # IPアドレスを取得
        print('Network config:', wlan.ifconfig())
        ipaddress = wlan.ifconfig()[0]

        # 接続状態とIPアドレスを表示
        dm.set_line(0, ipaddress, 8)
        dm.set_line(1, 'Connected!', 4)
        dm.show()

        # NTPサーバーから時刻を取得し、RTCに設定
        sync_ntp(dm)

        # NTP時刻取得完了メッセージ
        dm.set_line(2, 'Clock synced!', 4)
        dm.set_line(3, 'Booting up...', 4)
        dm.show()
        
    except Exception as e:
        dm.set_line(2, 'Error occurred,', 4)
        dm.set_line(3, 'Restarting...', 4)
        sleep(1)
        reset()
        
    dm.set_line(3, 'Booted!!', 4)
    dm.show()
    return led, sensor, dm

# 定数
UART_ID        = const(1)       # UART ID
I2C_ID         = const(0)       # I2C ID
I2C_FREQ       = const(400_000) # I2C バス速度
OLED_WIDTH     = const(128)     # OLEDの横ドット数
OLED_HEIGHT    = const(64)      # OLEDの縦ドット数
OLED_ADDR      = const(0x3c)    # OLEDのI2Cアドレス
OLED_SCL       = const(17)      # OLEDのSCLピン
OLED_SDA       = const(16)      # OLEDのSDAピン
SEND_INTERVAL  = const(300)     # 何秒間隔でデータを送信するか
EXIT_TRY       = const(2)       # プログラム終了までの猶予(0までカウントされる)
PRESS_TIME     = const(3900)    # ボタンを押してからスリープまでの時間(ミリ秒)
FLASH_TIME     = const(1000)    # LEDの点滅時間(ミリ秒)

i2c = I2C(I2C_ID, sda=Pin(OLED_SDA), scl=Pin(OLED_SCL), freq=I2C_FREQ)
display_ssd1306 = ssd1306.SSD1306_I2C_Extended(OLED_WIDTH, OLED_HEIGHT, i2c, addr=OLED_ADDR)
dm = DisplayManager(display_ssd1306)

# 初期化
led, sensor, dm = setup()
start_press_time = 0
start_led_time = 0
status_bootsel = False
status_before = dm.get_status()

# 少々待機してから開始
sleep(1)
dm.set_status(DisplayMode.RUNNING)

while True:
    # ボタンの長押しでスリープ及び解除
    if rp2.bootsel_button():
        if not status_bootsel:
            start_press_time = ticks_ms()
            before_status = dm.get_status()
        
        if before_status == dm.get_status():
            if ticks_diff(ticks_ms(), start_press_time) > PRESS_TIME:
                # スリープ状態の場合、スリープを解除
                if dm.get_status() == DisplayMode.SLEEP:
                    dm.set_line(0, 'Waking up...', 4)
                    dm.set_status(DisplayMode.RUNNING)
            
                # 非スリープ状態の場合はスリープに以降
                else:
                    dm.set_status(DisplayMode.SLEEP)
            elif dm.get_status() == DisplayMode.RUNNING:
                countdown_ms = PRESS_TIME - ticks_diff(ticks_ms(), start_press_time) # ミリ秒
                dm.set_line(0, str(countdown_ms // 1000) + ' to sleep', 4)
        status_bootsel = True

    # ボタンが押されていない場合
    else:
        # 現在時刻を取得
        hour, minute, second = get_jst()
        str_jst = '{:02d}:{:02d}:{:02d}'.format(hour, minute, second)
        dm.set_line(0, str_jst, 0)
        status_bootsel = False
    
    # CO2センサーからデータを取得
    try :
        sensor.get_data()
        dm.set_line(1, str(sensor.temp) + 'C', 16)
    except Exception as e:
        dm.set_line(0, 'Sensor', 4)
        dm.set_line(1, 'Failed..', 4)

    # 指定された頻度でデータベースに値を送信
    if (minute * 60 + second) % SEND_INTERVAL == 0:
        response = send_post(sensor.ppm, sensor.temp)
        dm.set_line(2, response, 4)
        print(response)
    else :
        dm.set_line(2, str(sensor.ppm) + 'ppm', 0)

    # 設定した表示を反映
    dm.show()
    
    # LED点滅
    if dm.get_status() == DisplayMode.RUNNING:
        if ticks_diff(ticks_ms(), start_led_time) > FLASH_TIME:
            start_led_time = ticks_ms()
            led.toggle()
    else :
        led.off()
