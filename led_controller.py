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

# LED strip configuration
LED_COUNT = 15
LED_PIN = 18  # GPIO18 (PWM0)
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 255
LED_INVERT = False
LED_CHANNEL = 0

# State file path
STATE_FILE = 'satellite_state.json'

# Initialize Flask app
app = Flask(__name__)

# Initialize NeoPixel strip
strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

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
    
    # Default state with transmission schedules for each LED
    default_state = {
        'solved': False,
        'led_states': [
            {
                'solved': False,
                'transmission_times': []
            } for _ in range(LED_COUNT)
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

def set_all_pixels(color):
    """Set all pixels to the specified color."""
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, color)
    strip.show()

def set_pixel_color(pixel_index, color):
    """Set a specific pixel to the specified color."""
    if 0 <= pixel_index < strip.numPixels():
        strip.setPixelColor(pixel_index, color)
        strip.show()

def update_led_state():
    """Update LED state based on satellite states."""
    while True:
        for i in range(LED_COUNT):
            led_state = satellite_states['led_states'][i]
            is_led_transmitting = is_transmitting(led_state['transmission_times'])
            
            if led_state['solved']:
                if is_led_transmitting:
                    # Alternating red and blue for solved and transmitting
                    set_pixel_color(i, Color(255, 0, 0))  # Red
                    time.sleep(0.5)
                    set_pixel_color(i, Color(0, 0, 255))  # Blue
                    time.sleep(0.5)
                else:
                    # Solid red for solved but not transmitting
                    set_pixel_color(i, Color(255, 0, 0))  # Red
                    time.sleep(1)
            else:
                if is_led_transmitting:
                    # Alternating green and blue for transmitting
                    set_pixel_color(i, Color(0, 255, 0))  # Green
                    time.sleep(0.5)
                    set_pixel_color(i, Color(0, 0, 255))  # Blue
                    time.sleep(0.5)
                else:
                    # Solid green for normal state
                    set_pixel_color(i, Color(0, 255, 0))  # Green
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
    led_index = data.get('led_index', 0)  # Default to first LED if not specified
    
    if not 0 <= led_index < LED_COUNT:
        return jsonify({'error': 'Invalid LED index'}), 400
    
    if event_type == 'challenge_solved':
        satellite_states['led_states'][led_index]['solved'] = True
        logging.info(f"Challenge solved for LED {led_index} - updating state")
    elif event_type == 'challenge_failed':
        satellite_states['led_states'][led_index]['solved'] = False
        logging.info(f"Challenge failed for LED {led_index} - updating state")
    elif event_type == 'add_transmission_time':
        transmission_times = data.get('transmission_times', [])
        if transmission_times:
            satellite_states['led_states'][led_index]['transmission_times'].extend(transmission_times)
            logging.info(f"Added transmission times for LED {led_index}: {transmission_times}")
    
    # Save state after any change
    save_state()
    
    return jsonify({'status': 'success'})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'satellite_states': satellite_states
    })

if __name__ == '__main__':
    # Log startup
    logging.info("Starting Satellite LED Controller")
    
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