# CTFd LED Controller

This project controls 15 NeoPixels connected to a Raspberry Pi 4, responding to webhooks from CTFd to simulate satellite states.

## Hardware Requirements

- Raspberry Pi 4
- 15 NeoPixels (WS2812B)
- Power supply for the NeoPixels (5V)
- Jumper wires
- Optional: Level shifter (if needed for your specific setup)

## Wiring

1. Connect the NeoPixels to the Raspberry Pi:
   - VCC (5V) → 5V on Raspberry Pi
   - GND → GND on Raspberry Pi
   - DIN (Data In) → GPIO18 (Pin 12) on Raspberry Pi

## Software Setup

1. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root:
   ```
   WEBHOOK_SECRET=your_secret_here
   PORT=5000
   ```

3. Enable SPI and PWM on your Raspberry Pi:
   ```bash
   sudo raspi-config
   ```
   Navigate to "Interface Options" and enable SPI and PWM.

## Running the Application

1. Run the application:
   ```bash
   sudo python3 led_controller.py
   ```
   Note: The application needs to run with sudo to access the GPIO pins.

2. The server will start on port 5000 (or the port specified in your .env file).

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
2024-03-14 10:00:00,000 - INFO - Starting Satellite LED Controller
2024-03-14 10:00:00,100 - INFO - Loaded state from file: {'transmitting': False, 'solved': False}
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
     - Challenge Failed
     - Add Transmission Time (custom event)

## Webhook Payloads

### Challenge Solved
```json
{
    "type": "challenge_solved",
    "led_index": 0  // Index of the LED (0-14)
}
```

### Challenge Failed
```json
{
    "type": "challenge_failed",
    "led_index": 0  // Index of the LED (0-14)
}
```

### Add Transmission Time
```json
{
    "type": "add_transmission_time",
    "led_index": 0,  // Index of the LED (0-14)
    "transmission_times": [
        ["2023/05/25 10:25:44", "2023/05/25 10:35:28"],
        ["2023/05/25 11:00:00", "2023/05/25 11:30:00"]
    ]
}
```

## Testing Webhooks

You can test the webhooks using curl commands. Replace `your_raspberry_pi_ip` with your actual Raspberry Pi's IP address and `your_secret` with your webhook secret.

### Mark LED 0 as Solved
```bash
curl -X POST http://your_raspberry_pi_ip:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "type": "challenge_solved",
    "led_index": 0
  }'
```

### Mark LED 1 as Failed
```bash
curl -X POST http://your_raspberry_pi_ip:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "type": "challenge_failed",
    "led_index": 1
  }'
```

### Add Transmission Times for LED 2
```bash
curl -X POST http://your_raspberry_pi_ip:5000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Webhook-Secret: your_secret" \
  -d '{
    "type": "add_transmission_time",
    "led_index": 2,
    "transmission_times": [
      ["2023/05/25 10:25:44", "2023/05/25 10:35:28"],
      ["2023/05/25 11:00:00", "2023/05/25 11:30:00"]
    ]
  }'
```

## LED Behavior

Each LED operates independently and displays different patterns based on its state:

- Normal State (Not Solved, Not Transmitting):
  - Solid Green

- Transmitting State (Not Solved, Transmitting):
  - Alternating Green and Blue (0.5s each)

- Solved State (Solved, Not Transmitting):
  - Solid Red

- Solved and Transmitting State (Solved, Transmitting):
  - Alternating Red and Blue (0.5s each)

## Health Check

You can check the current state of the system by accessing:
```
http://your_raspberry_pi_ip:5000/health
```
This will return the current satellite states for all LEDs, including their solved status and transmission schedules.

## Troubleshooting

1. If the LEDs don't respond:
   - Check the wiring connections
   - Ensure the power supply is sufficient
   - Verify the GPIO pin configuration
   - Check if the application is running with sudo

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