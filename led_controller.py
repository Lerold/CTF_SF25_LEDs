import os
import time
import json
import logging
from flask import Flask, request, jsonify
from rpi_ws281x import *
from dotenv import load_dotenv
import threading
from datetime import datetime
import traceback
import signal

# Load environment variables
load_dotenv('secret.env')

# Configure logging
logging.basicConfig(
    filename='satellite_led.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Load configuration from environment variables
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET', 'CTF_SF25_LEDs_Secret')
SATELLITE_COUNT = int(os.getenv('SATELLITE_COUNT', 10))  # Number of satellites
LEDS_PER_SATELLITE = int(os.getenv('LEDS_PER_SATELLITE', 2))  # Number of LEDs per satellite
TOTAL_LED_COUNT = SATELLITE_COUNT * LEDS_PER_SATELLITE  # Total number of LEDs
STATE_FILE = os.getenv('STATE_FILE', 'satellite_state.json')

# LED Colours (GRB format)
COLOURS = {
    'unsolved': (0, 255, 0),    # Red (GRB)
    'solved': (255, 0, 0),      # Green (GRB)
    'transmitting': (0, 0, 255) # Blue (GRB)
}

# LED Brightness (0-255)
BRIGHTNESS = {
    'unsolved': 50,    # Red brightness
    'solved': 50,      # Green brightness
    'transmitting': 100 # Blue brightness
}

# LED strip configuration
LED_PIN = 18  # GPIO18 (PWM0)
LED_FREQ_HZ = 800000  # LED signal frequency in Hz
LED_DMA = 10  # DMA channel to use for generating signal
LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
LED_INVERT = False  # True to invert the signal
LED_CHANNEL = 0  # PWM channel
LED_STRIP = ws.WS2811_STRIP_GRB  # Strip type and color ordering

# Global variables for graceful shutdown
running = True
led_thread = None
shutting_down = False
strip = None  # Make strip global so we can access it during shutdown
app = None  # Make Flask app global for shutdown
server = None  # Make server global for shutdown

def shutdown_server():
    """Shutdown the server gracefully."""
    global running, shutting_down, strip, server
    if not shutting_down:
        shutting_down = True
        print("\nReceived shutdown signal. Cleaning up...")
        running = False
        if strip:
            set_all_pixels(Color(0, 0, 0))  # Turn off all LEDs immediately
            strip.show()
        if server:
            server.shutdown()  # Stop the server
            server.server_close()  # Close the server socket
        os._exit(0)  # Force exit the program

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    # Start shutdown in a separate thread to avoid blocking
    threading.Thread(target=shutdown_server, daemon=True).start()

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Initialise Flask app
app = Flask(__name__)

# Add request logging middleware
@app.before_request
def log_request_info():
    print("\n=== Incoming Request ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"Headers: {dict(request.headers)}")
    print(f"Data: {request.get_data()}")
    print(f"WEBHOOK_SECRET from env: {WEBHOOK_SECRET}")
    print("=== End Request ===\n")

# Add error handler
@app.errorhandler(Exception)
def handle_error(error):
    print(f"\n=== Error Handler ===")
    print(f"Error: {str(error)}")
    print(f"Traceback: {traceback.format_exc()}")
    print("=== Error Handler End ===\n")
    return jsonify({'error': str(error)}), 500

# Initialise NeoPixel strip
strip = Adafruit_NeoPixel(TOTAL_LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
strip.begin()

def get_satellite_led_indices(satellite_index):
    """Get the LED indices for a specific satellite."""
    start_index = satellite_index * LEDS_PER_SATELLITE
    return range(start_index, start_index + LEDS_PER_SATELLITE)

# Log LED strip initialization
logging.info(f"Initialized LED strip with {TOTAL_LED_COUNT} LEDs ({SATELLITE_COUNT} satellites × {LEDS_PER_SATELLITE} LEDs per satellite)")
for i in range(SATELLITE_COUNT):
    led_indices = get_satellite_led_indices(i)
    logging.info(f"Satellite {i} controls LEDs: {list(led_indices)}")

# Initialize start time for LED timing
start_time = datetime.now()

def is_transmitting(transmission_times):
    """Check if a satellite is currently transmitting"""
    current_time = datetime.now()
    
    # If no transmission times, not transmitting
    if not transmission_times:
        return False
    
    # Check each transmission window
    for start_time_str, end_time_str in transmission_times:
        try:
            # Parse the times
            start_time = datetime.strptime(start_time_str, "%Y/%m/%d %H:%M:%S")
            end_time = datetime.strptime(end_time_str, "%Y/%m/%d %H:%M:%S")
            
            # If current time is within this window, satellite is transmitting
            if start_time <= current_time <= end_time:
                logging.debug(f"Satellite is transmitting: {start_time_str} to {end_time_str}")
                return True
        except ValueError as e:
            logging.error(f"Error parsing transmission time: {e}")
            continue
    
    # If we get here, we're not in any transmission window
    logging.debug("Satellite is not transmitting")
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
    """Update LED states based on satellite transmission times and solved status"""
    global start_time
    while running:  # Use the global running flag
        try:
            current_time = datetime.now()
            
            # Load current state
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                logging.debug(f"Loaded state: {state}")
            
            # Update each LED based on its satellite's state
            for satellite_index, satellite_state in enumerate(state['satellite_states']):
                # Get LED indices for this satellite
                led_indices = get_satellite_led_indices(satellite_index)
                
                # Check if satellite is currently transmitting
                transmitting_status = is_transmitting(satellite_state['transmission_times'])
                
                # Update each LED for this satellite
                for led_index in led_indices:
                    # Update LED based on state
                    if transmitting_status:
                        # If transmitting, alternate between state colour and blue
                        if satellite_state['solved']:
                            # Solved and transmitting: alternate between green and blue
                            if (current_time - start_time).total_seconds() % 1.0 < 0.5:
                                strip.setPixelColor(led_index, Color(0, BRIGHTNESS['solved'], 0))  # Green (GRB)
                                logging.debug(f"LED {led_index}: Setting green (solved)")
                            else:
                                strip.setPixelColor(led_index, Color(0, 0, BRIGHTNESS['transmitting']))  # Blue (GRB)
                                logging.debug(f"LED {led_index}: Setting blue (transmitting)")
                        else:
                            # Not solved and transmitting: alternate between red and blue
                            if (current_time - start_time).total_seconds() % 1.0 < 0.5:
                                strip.setPixelColor(led_index, Color(BRIGHTNESS['unsolved'], 0, 0))  # Red (GRB)
                                logging.debug(f"LED {led_index}: Setting red (unsolved)")
                            else:
                                strip.setPixelColor(led_index, Color(0, 0, BRIGHTNESS['transmitting']))  # Blue (GRB)
                                logging.debug(f"LED {led_index}: Setting blue (transmitting)")
                    else:
                        # If not transmitting, show solid state colour
                        if satellite_state['solved']:
                            # Solved: solid green
                            strip.setPixelColor(led_index, Color(0, BRIGHTNESS['solved'], 0))  # Green (GRB)
                            logging.debug(f"LED {led_index}: Setting solid green (solved)")
                        else:
                            # Not solved: solid red
                            strip.setPixelColor(led_index, Color(BRIGHTNESS['unsolved'], 0, 0))  # Red (GRB)
                            logging.debug(f"LED {led_index}: Setting solid red (unsolved)")
            
            strip.show()
            logging.debug("Updated all LEDs")
            time.sleep(0.1)  # Update every 100ms
            
        except Exception as e:
            print(f"Exception in thread Thread-1 (update_led_state):\n{traceback.format_exc()}")
            logging.error(f"Error in update_led_state: {e}")
            time.sleep(1)  # Wait before retrying

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle webhook events from CTFd"""
    try:
        # Log incoming request
        print("\n=== Webhook Request Received ===")
        print(f"Headers: {dict(request.headers)}")
        print(f"Raw Data: {request.get_data()}")
        print(f"WEBHOOK_SECRET from env: {WEBHOOK_SECRET}")
        
        # Verify webhook secret
        secret = request.headers.get('X-Webhook-Secret')
        print(f"Received secret: {secret}")
        print(f"Secret match: {secret == WEBHOOK_SECRET}")
        
        if not secret or secret != WEBHOOK_SECRET:
            print(f"Invalid or missing secret. Received: {secret}, Expected: {WEBHOOK_SECRET}")
            return jsonify({'error': 'Invalid webhook secret'}), 401
        
        # Parse request data
        data = request.get_json()
        if not data:
            print("No JSON data received")
            return jsonify({'error': 'No data provided'}), 400
            
        print(f"Parsed data: {data}")
        
        # Extract challenge ID and event type
        challenge_id = data.get('challenge_id')
        event_type = data.get('event')
        
        if challenge_id is None or event_type is None:
            print(f"Missing required fields. challenge_id: {challenge_id}, event: {event_type}")
            return jsonify({'error': 'Missing required fields'}), 400
            
        print(f"Processing challenge_id: {challenge_id}, event: {event_type}")
        
        # Load current state
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            print(f"Current state: {state}")
        
        # Update state based on event
        if event_type == 'solve':
            state['satellite_states'][challenge_id]['solved'] = True
            print(f"Set satellite {challenge_id} as solved")
        elif event_type == 'unsolve':
            state['satellite_states'][challenge_id]['solved'] = False
            print(f"Set satellite {challenge_id} as unsolved")
        else:
            print(f"Unknown event type: {event_type}")
            return jsonify({'error': 'Invalid event type'}), 400
        
        # Save updated state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
            
        print("State updated successfully")
        print("=== Webhook Request Completed ===\n")
        return jsonify({'status': 'success'})
        
    except Exception as e:
        print(f"\n=== Webhook Error ===")
        print(f"Error processing webhook: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        print("=== Webhook Error End ===\n")
        return jsonify({'error': str(e)}), 500

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

@app.route('/update_transmission_times', methods=['POST'])
def update_transmission_times():
    """Update transmission times for satellites"""
    try:
        # Verify webhook secret
        secret = request.headers.get('X-Webhook-Secret')
        if not secret or secret != WEBHOOK_SECRET:
            return jsonify({'error': 'Invalid webhook secret'}), 401
        
        # Parse request data
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        # Load current state
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Update transmission times
        for satellite_id, transmission_times in data.items():
            if 0 <= int(satellite_id) < SATELLITE_COUNT:
                state['satellite_states'][int(satellite_id)]['transmission_times'] = transmission_times
        
        # Save updated state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
            
        return jsonify({'status': 'success'})
        
    except Exception as e:
        logging.error(f"Error updating transmission times: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/clear_transmission_times', methods=['POST'])
def clear_transmission_times():
    """Clear all transmission times for satellites"""
    try:
        # Verify webhook secret
        secret = request.headers.get('X-Webhook-Secret')
        if not secret or secret != WEBHOOK_SECRET:
            return jsonify({'error': 'Invalid webhook secret'}), 401
            
        # Load current state
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Clear transmission times for all satellites
        for satellite in state['satellite_states']:
            satellite['transmission_times'] = []
        
        # Save updated state
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=4)
            
        return jsonify({'status': 'success', 'message': 'All transmission times cleared'})
        
    except Exception as e:
        logging.error(f"Error clearing transmission times: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/transmitting', methods=['GET'])
def get_transmitting_satellites():
    """Get list of currently transmitting satellites"""
    try:
        # Load current state
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
        
        # Check each satellite
        transmitting_satellites = []
        for i, satellite in enumerate(state['satellite_states']):
            if is_transmitting(satellite['transmission_times']):
                transmitting_satellites.append({
                    'satellite_id': i,
                    'solved': satellite['solved'],
                    'transmission_times': satellite['transmission_times']
                })
        
        return jsonify({
            'transmitting_count': len(transmitting_satellites),
            'transmitting_satellites': transmitting_satellites
        })
        
    except Exception as e:
        logging.error(f"Error getting transmitting satellites: {e}")
        return jsonify({'error': str(e)}), 500

def initialize_state_file():
    """Create or initialize the state file with default values"""
    try:
        # Check if file exists and is not empty
        if os.path.exists(STATE_FILE) and os.path.getsize(STATE_FILE) > 0:
            return
            
        # Create default state structure
        default_state = {
            "satellite_states": []
        }
        
        # Add states for each satellite
        for i in range(SATELLITE_COUNT):
            default_state["satellite_states"].append({
                "satellite_id": i,
                "solved": False,
                "transmission_times": []
            })
        
        # Save to file
        with open(STATE_FILE, 'w') as f:
            json.dump(default_state, f, indent=4)
            
        logging.info(f"Initialized state file with {SATELLITE_COUNT} satellites")
        
    except Exception as e:
        logging.error(f"Error initializing state file: {e}")
        raise

if __name__ == '__main__':
    try:
        # Initialize state file if needed
        initialize_state_file()
        
        # Start the LED control thread
        led_thread = threading.Thread(target=update_led_state, daemon=True)
        led_thread.start()
        
        # Get port from environment variable or use default
        port = int(os.getenv('PORT', 5000))
        
        # Log server start
        logging.info(f"Server starting on port {port}")
        
        # Create and start the server
        from werkzeug.serving import make_server
        server = make_server('0.0.0.0', port, app)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        shutdown_server()
    except Exception as e:
        logging.error(f"Error in main: {e}")
        shutdown_server() 