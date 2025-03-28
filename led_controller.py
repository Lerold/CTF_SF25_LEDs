import os
import time
import json
import logging
from flask import Flask, request, jsonify
from rpi_ws281x import *
from dotenv import load_dotenv
import threading
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    filename='satellite_led.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# LED Configuration
SATELLITE_COUNT = 10  # Number of satellites
LEDS_PER_SATELLITE = 3  # Number of LEDs per satellite
TOTAL_LED_COUNT = SATELLITE_COUNT * LEDS_PER_SATELLITE  # Total number of LEDs

# LED Colours (RGB format)
COLOURS = {
    'unsolved': (255, 0, 0),    # Red
    'solved': (0, 255, 0),      # Green
    'transmitting': (0, 0, 255) # Blue
}

# LED Brightness (0-255)
BRIGHTNESS = {
    'unsolved': 255,
    'solved': 255,
    'transmitting': 255
}

# LED strip configuration
LED_PIN = 18  # GPIO18 (PWM0)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# State file path
STATE_FILE = 'satellite_state.json'

# Initialise Flask app
app = Flask(__name__)

# Initialise NeoPixel strip
strip = Adafruit_NeoPixel(TOTAL_LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def get_satellite_led_indices(satellite_index):
    """Get the LED indices for a specific satellite."""
    start_index = satellite_index * LEDS_PER_SATELLITE
    return range(start_index, start_index + LEDS_PER_SATELLITE)

def is_transmitting(transmission_times):
    """Check if current time falls within any transmission window."""
    current_time = datetime.now()
    for start_time, end_time in transmission_times:
        start = datetime.strptime(start_time, "%Y/%m/%d %H:%M:%S")
        end = datetime.strptime(end_time, "%Y/%m/%d %H:%M:%S")
        if start <= current_time <= end:
            return True
    return False

def load_state():
    """Load satellite state from file."""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logging.info(f"Loaded state from file: {state}")
                return state
    except Exception as e:
        logging.error(f"Error loading state: {e}")
    
    # Default state with transmission schedules for each satellite
    default_state = {
        'satellite_states': [
            {
                'solved': False,
                'transmission_times': []
            } for _ in range(SATELLITE_COUNT)
        ]
    }
    return default_state

def save_state():
    """Save current satellite state to file."""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(satellite_states, f)
            logging.info(f"Saved state to file: {satellite_states}")
    except Exception as e:
        logging.error(f"Error saving state: {e}")

# Global state
satellite_states = load_state()

def set_all_pixels(colour):
    """Set all pixels to the specified colour."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, colour)
    strip.show()

def set_pixel_colour(pixel_index, colour):
    """Set a specific pixel to the specified colour."""
    if 0 <= pixel_index < strip.numPixels():
        strip.setPixelColor(pixel_index, colour)
        strip.show()

def set_satellite_leds(satellite_index, colour):
    """Set all LEDs for a specific satellite to the given colour."""
    for led_index in get_satellite_led_indices(satellite_index):
        set_pixel_colour(led_index, colour)

def update_led_state():
    """Update LED state based on satellite states."""
    while True:
        for satellite_index in range(SATELLITE_COUNT):
            satellite_state = satellite_states['satellite_states'][satellite_index]
            is_transmitting = is_transmitting(satellite_state['transmission_times'])
            
            if satellite_state['solved']:
                if is_transmitting:
                    # Alternating green and blue for solved and transmitting
                    set_satellite_leds(satellite_index, Color(*COLOURS['solved']))
                    time.sleep(0.5)
                    set_satellite_leds(satellite_index, Color(*COLOURS['transmitting']))
                    time.sleep(0.5)
                else:
                    # Solid green for solved but not transmitting
                    set_satellite_leds(satellite_index, Color(*COLOURS['solved']))
                    time.sleep(1)
            else:
                if is_transmitting:
                    # Alternating red and blue for transmitting
                    set_satellite_leds(satellite_index, Color(*COLOURS['unsolved']))
                    time.sleep(0.5)
                    set_satellite_leds(satellite_index, Color(*COLOURS['transmitting']))
                    time.sleep(0.5)
                else:
                    # Solid red for normal state
                    set_satellite_leds(satellite_index, Color(*COLOURS['unsolved']))
                    time.sleep(1)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhooks from CTFd."""
    data = request.get_json()
    
    # Log incoming webhook
    logging.info(f"Received webhook: {data}")
    
    # Verify webhook secret if configured
    webhook_secret = os.getenv('WEBHOOK_SECRET')
    if webhook_secret:
        received_secret = request.headers.get('X-Webhook-Secret')
        if not received_secret or received_secret != webhook_secret:
            logging.warning("Invalid webhook secret received")
            return jsonify({'error': 'Invalid webhook secret'}), 401

    # Handle different webhook events
    event_type = data.get('type')
    satellite_index = data.get('satellite_index', 0)  # Default to first satellite if not specified
    
    if not 0 <= satellite_index < SATELLITE_COUNT:
        return jsonify({'error': f'Invalid satellite index. Must be between 0 and {SATELLITE_COUNT-1}'}), 400
    
    if event_type == 'challenge_solved':
        satellite_states['satellite_states'][satellite_index]['solved'] = True
        logging.info(f"Challenge solved for satellite {satellite_index} - updating state")
    elif event_type == 'add_transmission_time':
        transmission_times = data.get('transmission_times', [])
        if transmission_times:
            satellite_states['satellite_states'][satellite_index]['transmission_times'].extend(transmission_times)
            logging.info(f"Added transmission times for satellite {satellite_index}: {transmission_times}")
    
    # Save state after any change
    save_state()
    
    return jsonify({'status': 'success'})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'satellite_count': SATELLITE_COUNT,
        'leds_per_satellite': LEDS_PER_SATELLITE,
        'total_led_count': TOTAL_LED_COUNT,
        'satellite_states': satellite_states
    })

if __name__ == '__main__':
    # Log startup
    logging.info(f"Starting Satellite LED Controller with {SATELLITE_COUNT} satellites and {LEDS_PER_SATELLITE} LEDs per satellite")
    
    # Turn off all pixels on startup
    set_all_pixels(Color(0, 0, 0))
    
    # Start the LED update thread
    led_thread = threading.Thread(target=update_led_state, daemon=True)
    led_thread.start()
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))
    
    # Log server start
    logging.info(f"Server starting on port {port}")
    
    # Start the Flask server
    app.run(host='0.0.0.0', port=port) 