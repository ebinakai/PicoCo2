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
