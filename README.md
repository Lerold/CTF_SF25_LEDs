# CTFd LED Controller

This project controls NeoPixels connected to a Raspberry Pi 4, responding to webhooks from CTFd to simulate satellite states. Each satellite can have multiple LEDs, and the system supports customisable colours and brightness levels.

## Hardware Requirements

- Raspberry Pi 4
- NeoPixels (WS2812B) - configurable number of LEDs per satellite
- Power supply for the NeoPixels (5V)
- Jumper wires
- Optional: Level shifter (if needed for your specific setup)

## Configuration

The system can be configured by modifying the following variables in `led_controller.py`:

```python
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
```

## Wiring

1. Connect the NeoPixels to the Raspberry Pi:
   - VCC (5V) → 5V on Raspberry Pi
   - GND → GND on Raspberry Pi
   - DIN (Data In) → GPIO18 (Pin 12) on Raspberry Pi

## Software Setup

1. Set up a Python virtual environment (recommended):
   ```bash
   # Install virtualenv if you haven't already
   sudo apt-get update
   sudo apt-get install python3-venv

   # Create a new virtual environment
   python3 -m venv venv

   # Activate the virtual environment
   source venv/bin/activate

   # Your prompt should now show (venv) at the beginning
   ```

2. Install the required packages:
   ```bash
   # Make sure you're in the virtual environment (you should see (venv) in your prompt)
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root:
   ```
   WEBHOOK_SECRET=your_secret_here
   PORT=5000
   ```

4. Configure the number of satellites and LEDs per satellite:
   - Open `led_controller.py`
   - Find the `SATELLITE_COUNT` and `LEDS_PER_SATELLITE` variables at the top of the file
   - Change the values to match your setup

5. Enable SPI and PWM on your Raspberry Pi:
   ```bash
   sudo raspi-config
   ```
   Navigate to "Interface Options" and enable SPI and PWM.

## Running the Application

1. Make sure your virtual environment is activated:
   ```bash
   source venv/bin/activate
   ```

2. Run the application with sudo (use one of these methods):

   #### Method 1: Using the virtual environment's Python directly
   ```bash
   # Get the full path to your virtual environment's Python
   which python3
   
   # Use that path with sudo
   sudo /full/path/to/venv/bin/python3 led_controller.py
   ```

   #### Method 2: Using a shell script (recommended for development)
   Create a file called `run_led_controller.sh`:
   ```bash
   #!/bin/bash
   source /full/path/to/venv/bin/activate
   python3 led_controller.py
   ```
   
   Make it executable:
   ```bash
   chmod +x run_led_controller.sh
   ```
   
   Run it with sudo:
   ```bash
   sudo ./run_led_controller.sh
   ```

   #### Method 3: Create a systemd service (recommended for production)
   1. Create a service file:
      ```bash
      sudo nano /etc/systemd/system/satellite-led.service
      ```

   2. Add the following content (replace paths with your actual paths):
      ```ini
      [Unit]
      Description=Satellite LED Controller
      After=network.target

      [Service]
      Type=simple
      User=root
      WorkingDirectory=/path/to/your/project
      Environment=PATH=/path/to/your/venv/bin
      Environment=PYTHONPATH=/path/to/your/venv/lib/python3.x/site-packages
      ExecStart=/path/to/your/venv/bin/python3 led_controller.py
      Restart=always

      [Install]
      WantedBy=multi-user.target
      ```

   3. Enable and start the service:
      ```bash
      sudo systemctl daemon-reload
      sudo systemctl enable satellite-led
      sudo systemctl start satellite-led
      ```

   4. Check the status:
      ```bash
      sudo systemctl status satellite-led
      ```

3. The server will start on port 5000 (or the port specified in your .env file).

### Important Notes About Running with sudo

When running the application with sudo, you need to ensure the virtual environment is properly accessible. The methods above handle this in different ways:

- Method 1 is the most direct but requires typing the full path
- Method 2 is convenient for development but requires creating a shell script
- Method 3 is the most robust for production use

Choose the method that best suits your needs. For development, Method 2 is recommended. For production, Method 3 is the best choice.

## State Persistence and Logging

The application includes two important features for monitoring and maintaining state:

### State Persistence
- The current state (transmitting and solved status) is automatically saved to `satellite_state.json`
- When the application restarts, it will load the last known state
- This ensures the LED display maintains the correct state even after power outages or restarts

### Logging
- All events are logged to `satellite_led.log`
- The log file includes:
  - Application startup and shutdown times
  - All received webhooks
  - State changes
  - Any errors or warnings
- Log format: `timestamp - level - message`

Example log entries:
```
2024-03-14 10:00:00,000 - INFO - Starting Satellite LED Controller with 10 satellites and 3 LEDs per satellite
2024-03-14 10:00:00,100 - INFO - Loaded state from file: {'satellite_states': [...]}
2024-03-14 10:00:00,200 - INFO - Server starting on port 5000
2024-03-14 10:05:00,000 - INFO - Received webhook: {'type': 'transmission_start'}
2024-03-14 10:05:00,100 - INFO - Transmission started - updating state
```

## CTFd Webhook Configuration

1. In your CTFd admin panel, go to Config → Integrations
2. Add a new webhook with the following settings:
   - URL: `http://your_raspberry_pi_ip:5000/webhook`
   - Secret: The same secret you set in your .env file
   - Events to trigger webhook:
     - Challenge Solved
     - Add Transmission Time (custom event)

## Webhook Payloads

### Challenge Solved
```json
{
    "type": "challenge_solved",
    "satellite_index": 0  // Index of the satellite (0 to SATELLITE_COUNT-1)
}
```

### Add Transmission Time
```json
{
    "type": "add_transmission_time",
    "satellite_index": 0,  // Index of the satellite (0 to SATELLITE_COUNT-1)
    "transmission_times": [
        ["2023/05/25 10:25:44", "2023/05/25 10:35:28"],
        ["2023/05/25 11:00:00", "2023/05/25 11:30:00"]
    ]
}
```

## Testing Webhooks

You can test the webhooks using curl commands. Replace `your_raspberry_pi_ip` with your actual Raspberry Pi's IP address and `your_secret` with your webhook secret.

### Mark Satellite 0 as Solved
```bash
curl -X POST http://your_raspberry_pi_ip:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "type": "challenge_solved",
    "satellite_index": 0
  }'
```

### Add Transmission Times for Satellite 2
```bash
curl -X POST http://your_raspberry_pi_ip:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "type": "add_transmission_time",
    "satellite_index": 2,
    "transmission_times": [
      ["2023/05/25 10:25:44", "2023/05/25 10:35:28"],
      ["2023/05/25 11:00:00", "2023/05/25 11:30:00"]
    ]
  }'
```

## LED Behaviour

Each satellite's LEDs operate together and display different patterns based on the satellite's state:

- Normal State (Not Solved, Not Transmitting):
  - Solid Red
  - This is the default state for unsolved challenges

- Transmitting State (Not Solved, Transmitting):
  - Alternating Red and Blue (0.5s each)
  - Indicates active transmission window for an unsolved challenge

- Solved State (Solved, Not Transmitting):
  - Solid Green
  - Indicates a successfully solved challenge

- Solved and Transmitting State (Solved, Transmitting):
  - Alternating Green and Blue (0.5s each)
  - Indicates active transmission window for a solved challenge

## Health Check

You can check the current state of the system by accessing:
```
http://your_raspberry_pi_ip:5000/health
```
This will return the current satellite states, including:
- Number of satellites
- LEDs per satellite
- Total LED count
- Current state of each satellite

## Troubleshooting

1. If the LEDs don't respond:
   - Check the wiring connections
   - Ensure the power supply is sufficient
   - Verify the GPIO pin configuration
   - Check if the application is running with sudo
   - Verify the total LED count matches your physical setup

2. If webhooks aren't working:
   - Verify the webhook URL is correct
   - Check if the webhook secret matches
   - Ensure the Raspberry Pi is accessible from the CTFd server
   - Verify that the custom events are properly configured in CTFd

3. For state or logging issues:
   - Check the permissions of `satellite_state.json` and `satellite_led.log`
   - Ensure there's enough disk space for logging
   - Check the log file for any error messages

4. For transmission time issues:
   - Verify the date/time format is correct (YYYY/MM/DD HH:MM:SS)
   - Check that the system time is correctly set
   - Ensure transmission times are in chronological order

5. For LED count issues:
   - Verify that `SATELLITE_COUNT` and `LEDS_PER_SATELLITE` in `led_controller.py` match your actual setup
   - Ensure all satellite indices in webhook calls are within the valid range (0 to SATELLITE_COUNT-1)
   - Check that the total LED count matches your physical LED strip length