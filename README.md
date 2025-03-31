# Satellite LED Controller

A Python application that controls NeoPixel LEDs on a Raspberry Pi to display satellite transmission states and challenge completion status for CTF challenges.

## Features

- Controls 10 NeoPixel LEDs (WS2812) connected to GPIO18
- Displays satellite transmission states and challenge completion status
- Responds to webhooks from CTFd for real-time updates
- Supports customisable colours and brightness levels
- Graceful shutdown handling
- Health check endpoint

## Hardware Requirements

- Raspberry Pi 4 (or compatible)
- 10 WS2812 NeoPixel LEDs
- Jumper wires
- 5V power supply
- 300-500Ω resistor (for data line protection)

## Wiring

1. Connect the NeoPixel data line to GPIO18 (Pin 12) through a 300-500Ω resistor
2. Connect VCC to 5V
3. Connect GND to any ground pin
4. Connect a large capacitor (1000µF) between 5V and GND near the first pixel for power stability

## Software Requirements

- Python 3.7+
- Required Python packages (install via `pip install -r requirements.txt`):
  - flask
  - rpi_ws281x
  - python-dotenv

## Installation

1. Clone this repository:
   ```bash
   git clone <repository-url>
   cd CTF_SF25_LEDs
   ```

2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `secret.env` file with your configuration:
   ```env
   WEBHOOK_SECRET=your_secret_here
   PORT=5000
   SATELLITE_COUNT=10
   LEDS_PER_SATELLITE=1
   STATE_FILE=satellite_state.json
   ```

4. Create initial state file:
   ```bash
   python3 create_state.py
   ```

## Usage

1. Run the application with sudo (required for GPIO access):
   ```bash
   sudo python3 led_controller.py
   ```

2. The application will:
   - Initialize the LED strip
   - Start the web server on port 5000
   - Begin monitoring satellite states

## LED Behaviour

The LEDs use GRB color ordering (not RGB) and display the following states:

- Normal State (Not Solved, Not Transmitting): Solid Red
- Transmitting State (Not Solved, Transmitting): Alternating Red and Blue
- Solved State (Solved, Not Transmitting): Solid Green
- Solved and Transmitting State (Solved, Transmitting): Alternating Green and Blue

Timing:
- Alternating states change every 0.5 seconds
- Solid states remain constant
- LED updates occur every 100ms

## Testing the Webhook

You can test the webhook functionality using curl commands:

1. Test solving a challenge (e.g., satellite 0):
   ```bash
   curl -X POST http://localhost:5000/webhook \
   -H "Content-Type: application/json" \
   -H "X-Webhook-Secret: your_secret_here" \
   -d '{
       "challenge_id": 0,
       "event": "solve"
   }'
   ```

2. Test unsolving a challenge:
   ```bash
   curl -X POST http://localhost:5000/webhook \
   -H "Content-Type: application/json" \
   -H "X-Webhook-Secret: your_secret_here" \
   -d '{
       "challenge_id": 0,
       "event": "unsolve"
   }'
   ```

3. Check the health endpoint:
   ```bash
   curl http://localhost:5000/health
   ```

## Troubleshooting

1. If LEDs don't light up:
   - Check wiring connections
   - Verify power supply is adequate
   - Check if running with sudo
   - Verify GPIO18 is not in use by another process

2. If webhooks aren't working:
   - Check the webhook secret matches in CTFd and secret.env
   - Verify the server is running and accessible
   - Check the logs for any errors

3. If colors are incorrect:
   - The LEDs use GRB color ordering, not RGB
   - Verify the color values in the code match your expectations

## Logging

The application logs to `satellite_led.log` with the following information:
- Server startup and configuration
- Webhook requests and responses
- LED state changes
- Errors and exceptions

## License

[Your License Here]