# Satellite LED Controller

A Python application for controlling NeoPixel LEDs on a Raspberry Pi to display satellite transmission states. The LEDs change colour based on whether a satellite is transmitting and whether its challenge has been solved.

## Features

- Controls NeoPixel LEDs on a Raspberry Pi
- Responds to webhooks from CTFd for challenge solve/unsolve events
- Displays satellite transmission states with different LED colours
- Includes health check endpoint
- Supports updating transmission times via webhook
- Provides endpoints to clear transmission times and query transmitting satellites

## Hardware Requirements

- Raspberry Pi 4
- WS2812 NeoPixel LEDs
- Power supply for LEDs
- Jumper wires for connecting LEDs to GPIO

## Software Requirements

- Python 3.7+
- Flask
- rpi_ws281x
- python-dotenv

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/CTF_SF25_LEDs.git
   cd CTF_SF25_LEDs
   ```

2. Install required packages:
   ```bash
   pip3 install -r requirements.txt
   ```

3. Create a `secret.env` file with your configuration:
   ```
   WEBHOOK_SECRET=your_secret_here
   PORT=5000
   SATELLITE_COUNT=10
   LEDS_PER_SATELLITE=1
   STATE_FILE=satellite_state.json
   ```

## Usage

1. Run the application with sudo (required for GPIO access):
   ```bash
   sudo python3 led_controller.py
   ```

2. The LEDs will display:
   - Red: Unsolved satellite
   - Green: Solved satellite
   - Blue: Currently transmitting satellite
   - Alternating Red/Blue: Unsolved satellite that is transmitting
   - Alternating Green/Blue: Solved satellite that is transmitting

## Testing the Webhook

You can test the webhook functionality using curl commands:

1. Solve a challenge:
   ```bash
   curl -X POST http://localhost:5000/webhook \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: super_secret" \
     -d '{"challenge_id": 0, "event": "solve"}'
   ```

2. Unsolve a challenge:
   ```bash
   curl -X POST http://localhost:5000/webhook \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: super_secret" \
     -d '{"challenge_id": 0, "event": "unsolve"}'
   ```

3. Update transmission times:
   ```bash
   curl -X POST http://localhost:5000/update_transmission_times \
     -H "Content-Type: application/json" \
     -H "X-Webhook-Secret: super_secret" \
     -d '{
       "0": [["2024/03/31 10:00:00", "2024/03/31 10:30:00"]],
       "1": [["2024/03/31 10:30:00", "2024/03/31 11:00:00"]]
     }'
   ```

4. Clear all transmission times:
   ```bash
   curl -X POST http://localhost:5000/clear_transmission_times \
     -H "X-Webhook-Secret: super_secret"
   ```

5. Check which satellites are currently transmitting:
   ```bash
   curl http://localhost:5000/transmitting
   ```

6. Check the health endpoint:
   ```bash
   curl http://localhost:5000/health
   ```

## Troubleshooting

1. If the LEDs are not responding:
   - Check the wiring connections
   - Verify the GPIO pin number in the code
   - Ensure the power supply is adequate

2. If webhooks are not working:
   - Verify the webhook secret in your `secret.env` file
   - Check the server logs for any errors
   - Ensure the server is running with sudo privileges

3. If transmission times are not updating:
   - Verify the date format is correct (YYYY/MM/DD HH:MM:SS)
   - Check that the satellite IDs are within range
   - Ensure the webhook secret is correct

## Logging

The application logs all activities to `satellite_led.log`. You can monitor the log file in real-time using:
```bash
tail -f satellite_led.log
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.