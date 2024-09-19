# Birdwatcher
This project is Dockerized. Its main task is to access RSS data from Nitter and post it in a Discord text channel via a webhook.

> [!IMPORTANT]
> You must host your own Nitter instance. Frequently using public Nitter instances may result in being blocked from their service. [Check out this guide for self-hosting Nitter](https://github.com/sekai-soft/guide-nitter-self-hosting).

## Installation
1. Clone this repository.
2. In Discord, right-click on the desired channel and select 'Edit Channel.'
3. In the channel settings, click 'Integrations' on the left sidebar, then click the 'Create Webhook' button.
4. Discord will generate a webhook name. You may rename it if you wish. Click the right arrow to expand the webhook settings, then click the 'Copy Webhook URL' button.
5. Copy the Webhook URL and paste it as `WEBHOOK_URL` into the [Dockerfile](https://github.com/BatteryDie/birdwatcher/blob/main/Dockerfile) or Docker Compose.
    1. If running the Python file directly, paste it as `WEBHOOK_URL` into the `.env` file. Please refer to the Environment Variables Example.
6. Set the `BIRD_USER`, `INTERVAL`, `NITTER_INSTANCE`, and `COLOUR` values in the [Dockerfile](https://github.com/BatteryDie/birdwatcher/blob/main/Dockerfile) or Docker Compose.
    1. If running the Python file directly, set these values in the `.env` file. Please refer to the Environment Variables Example.
7. Build the Docker image or run the Python file!
    1. If running the Python file directly, first execute `pip install -r requirements.txt`.

## Environment Variables

- `WEBHOOK_URL`: The URL of the Discord webhook where the RSS feed updates will be posted. You can get this from the Discord channel’s webhook settings.
- `NITTER_INSTANCE`: The URL of your self-hosted Nitter instance (e.g., `https://nitter.local`). Nitter is used to fetch Twitter feeds via RSS.
- `BIRD_USER`: The Twitter username that you want to monitor for updates via Nitter. This should be the Twitter handle (e.g., `JohnAppleseed98`).
- `INTERVAL`: The time interval (in seconds) between RSS feed checks. For example, `300` would check for updates every 5 minutes.
- `COLOUR`: The color (in int format) for the embed messages in Discord. This determines the color of the left-hand stripe on embeds. You can refer to this [list of Discord embed colors](https://gist.github.com/thomasbnt/b6f455e2c7d743b796917fa3c205f812) for pre-selected colors in int format.

## Environment Variables Example
```
BIRD_USER=JohnAppleseed98
INTERVAL=300
NITTER_INSTANCE=https://nitter.local
WEBHOOK_URL=https://discord.com/api/webhooks/XXXXXXXXXXXX 
COLOUR=5763719
```
