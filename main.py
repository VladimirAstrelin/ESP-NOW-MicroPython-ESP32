from machine import Pin, SoftI2C
import ssd1306
import network
import espnow
import utime

# ===== КОНФИГУРАЦИЯ =====
DEVICE_TYPE = 'SENDER'  # Указать 'SENDER' для одной платы и 'RECEIVER' для второй платы

# Настройки пинов
I2C_SCL_PIN = 22
I2C_SDA_PIN = 21
BUTTON_PIN = 0     # Встроенная Кнопка (BOOT button)
LED_PIN = 2        # Встроенный Cветодиод

# MAC-адреса устройств (у каждой платы свой MAC-адрес ! у Отправителя свой MAC, у Получателя свой MAC)
PEER_MAC = b'\xa0\xb7e\xf5d\x94' if DEVICE_TYPE == 'SENDER' else b'\xa0\xb7eko8'

# ===== ИНИЦИАЛИЗАЦИЯ ДИСПЛЕЯ =====
i2c = SoftI2C(scl=Pin(I2C_SCL_PIN), sda=Pin(I2C_SDA_PIN))
oled = ssd1306.SSD1306_I2C(128, 64, i2c)

def display_status(status):
    """Обновляем статус на дисплее"""
    oled.fill(0)
    oled.text(f"{DEVICE_TYPE}", 0, 0)
    oled.text("Remote LED:", 0, 20)
    oled.text(status, 0, 40)
    oled.show()

# ===== НАСТРОЙКА ESP-NOW =====
def setup_espnow():
    """Инициализация ESP-NOW"""
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.disconnect()
    
    esp = espnow.ESPNow()
    esp.active(True)
    esp.add_peer(PEER_MAC)
    return esp

# ===== ОСНОВНЫЕ ФУНКЦИИ =====
def handle_message(msg):
    """Обработка входящих сообщений"""
    if msg == b'ledOn':
        led.on()
        return b'ACK_ON'
    elif msg == b'ledOff':
        led.off()
        return b'ACK_OFF'
    return None

def send_command(esp, command):
    """Отправка команды и получение ответа"""
    try:
        esp.send(PEER_MAC, command)
        
        # Ожидаем ответ 300мс
        start = utime.ticks_ms()
        while utime.ticks_diff(utime.ticks_ms(), start) < 300:
            sender, response = esp.recv()
            if response:
                return response
        return None
    except Exception as e:
        print("Send error:", e)
        return None

# ===== ИНИЦИАЛИЗАЦИЯ =====
oled.fill(0)
oled.text("Starting...", 0, 0)
oled.show()

led = Pin(LED_PIN, Pin.OUT)
led.off()
esp = setup_espnow()

button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)
last_button_state = button.value()
display_status("READY")

# ===== ГЛАВНЫЙ ЦИКЛ =====
while True:
    # 1. Обработка кнопки (отправка команд)
    current_state = button.value()
    if current_state != last_button_state:
        utime.sleep_ms(50)  # Дребезг
        current_state = button.value()
        
        if current_state != last_button_state:
            if current_state == 0:  # Кнопка нажата
                response = send_command(esp, b'ledOn')
                status = "ON" if response == b'ACK_ON' else "ERR"
            else:  # Кнопка отпущена
                response = send_command(esp, b'ledOff')
                status = "OFF" if response == b'ACK_OFF' else "ERR"
            
            display_status(status)
            last_button_state = current_state
    
    # 2. Проверка входящих сообщений
    try:
        sender, msg = esp.recv(100)  # Неблокирующее чтение
        if msg:
            response = handle_message(msg)
            if response:
                esp.send(sender, response)
    except Exception as e:
        print("Recv error:", e)
    
    utime.sleep_ms(10)