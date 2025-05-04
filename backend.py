import logging
import RPi.GPIO as GPIO
import smbus

# I2C-konfigurasjon
I2C_CHANNEL = 1
SOLAR_ADDRESS = 0x40
BATTERY_ADDRESS = 0x41

CONFIG_REGISTER = 0x00
CALIBRATION_REGISTER = 0x05
BUS_VOLTAGE_REGISTER = 0x02
CURRENT_REGISTER = 0x04

DEFAULT_CONFIG = 0x399F
CALIBRATION_VALUE = 4096

# GPIO-oppsett
RELAY_PIN = 24
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Logging
logging.basicConfig(filename="charging_control_log.txt", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")

# Start I2C
bus = smbus.SMBus(I2C_CHANNEL)

# Grenser for hysterese
LOW_VOLTAGE_THRESHOLD = 3.6
HIGH_VOLTAGE_THRESHOLD = 3.7

# Intern status
charging_from_generator = False

def write_config(address):
    config = DEFAULT_CONFIG
    config_swapped = ((config & 0xFF) << 8) | ((config >> 8) & 0xFF)
    bus.write_word_data(address, CONFIG_REGISTER, config_swapped)

def write_calibration(address):
    calibration = CALIBRATION_VALUE
    calibration_swapped = ((calibration & 0xFF) << 8) | ((calibration >> 8) & 0xFF)
    bus.write_word_data(address, CALIBRATION_REGISTER, calibration_swapped)

def read_bus_voltage(address):
    raw = bus.read_word_data(address, BUS_VOLTAGE_REGISTER)
    raw_swapped = ((raw & 0xFF) << 8) | (raw >> 8)
    voltage_bits = raw_swapped >> 3
    return voltage_bits * 0.004  # V

def read_current(address):
    raw = bus.read_word_data(address, CURRENT_REGISTER)
    raw_swapped = ((raw & 0xFF) << 8) | (raw >> 8)
    if raw_swapped > 32767:
        raw_swapped -= 65536
    return raw_swapped * 0.001  # A

def control_relay():
    global charging_from_generator

    try:
        solar_voltage = read_bus_voltage(SOLAR_ADDRESS)
        solar_current = read_current(SOLAR_ADDRESS)
        solar_power = solar_voltage * solar_current

        battery_voltage = read_bus_voltage(BATTERY_ADDRESS)

        logging.info(f"SOL: {solar_voltage:.2f} V, {solar_current*1000:.0f} mA, {solar_power:.2f} W | BAT: {battery_voltage:.2f} V")

        # Hysterese-logikk
        if battery_voltage <= LOW_VOLTAGE_THRESHOLD:
            charging_from_generator = True
        elif battery_voltage >= HIGH_VOLTAGE_THRESHOLD:
            charging_from_generator = False

        if charging_from_generator:
            GPIO.output(RELAY_PIN, GPIO.LOW)
            status = "Generator aktivert(Bat<=3.6V)"
        else:
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            status = "Solcelle aktivert (BAT >= 3.7 v)"

        return {
            "solar_voltage": round(solar_voltage, 2),
            "solar_current": round(solar_current * 1000, 1),
            "solar_power": round(solar_power, 2),
            "battery_voltage": round(battery_voltage, 2),
            "status": status
        }

    except Exception as e:
        logging.error("Feil under kontroll: " + str(e))
        return {
            "solar_voltage": 0,
            "solar_current": 0,
            "solar_power": 0,
            "battery_voltage": 0,
            "status": "Sensorfeil"
        }

def cleanup():
    GPIO.cleanup()

# Init ved oppstart
write_config(SOLAR_ADDRESS)
write_calibration(SOLAR_ADDRESS)

write_config(BATTERY_ADDRESS)
write_calibration(BATTERY_ADDRESS)