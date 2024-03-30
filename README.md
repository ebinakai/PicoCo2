# PicoCO2

Raspberry Pi PicoによるCO2センサー MHZ-19 の測定を行うプログラム  
VSCodeの拡張機能 `MicroPico` を使用して開発しました。

## ファイル構造

```bash
.
├── env.py        # Wifi情報やAPI情報を追記
├── main.py       # メインプログラム
├── mhz19.py      # CO2センサのライブラリ
└── ssd1306.py    # OLEDディスプレイのライブラリ
```

## 配線

OLEDディスプレイのSDAを16番ピンに、SCLを17番ピンに接続しています。変更する場合はメインプログラム中の `OLED_SCL`, `OLED_SDA` を変更してください。

CO2センサ（MHZ-19）は、RXを4番ピンにTXを5番ピンに接続して、UART1番を使用しています。  
センサー側のTXとマイコン側のRX、センサー側のRXとマイコン側のTXを接続してください。

タクトスイッチを `GND` と `PIN-21` に接続してください。

## ネットワーク設定

`env.py` にネットワーク情報を記入してください

```python
WIFI_SSID = 'wifi-ssid'
WIFI_PASSWORD = 'wifi-password'
API_URL = 'your-api-endpoint'
```

`main.py` 内の `SEND_EVERY_SEC` に設定した秒数に一度、`API_URL`に指定したエンドポイントに温度センサとCO2センサの値を以下の形式で送信されます。

```json
[
  {"name": "co2", "value": 1500},
  {"name": "temp", "value": 18}
]
```

## 使い方

1. MicroUSBをPicoに接続します
2. 指定したネットワークに接続します
3. 0.8秒感覚でセンサーの値を取得します。LEDは点滅します
4. `PIN-21` に接続したタクトスイッチを押下すると、画面の表示・非表示が切り替えられますが、センサの計測は継続されます。LEDは点灯します。
5. Pico の Bootsellボタン を三秒ほど押下するとスリープ状態に移行し、画面が消えてセンサの計測も停止されます。LEDが消灯します。
6. スリープ状態時に Bootsellボタン を三秒ほど押下するとスリープ状態が解除されます。

## ライブラリ

以下のライブラリを使用しています。

- [https://pypi.org/project/micropython-ssd1306](https://pypi.org/project/micropython-ssd1306)  
- [https://github.com/overflo23/MH-Z19_MicroPython](https://github.com/overflo23/MH-Z19_MicroPython)
