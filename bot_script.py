import logging
import os
import json
import subprocess
import asyncio
from telethon import TelegramClient, events
from dotenv import load_dotenv
import requests  # Import requests for API calls


# Assuming the total supply is constant
total_supply = 231_379_500_000_000  # Your total supply

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load the environment variables from the current directory
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'api.env')
load_dotenv(dotenv_path=env_path)

TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHANNEL_IDENTIFIER = '-1002014930628'  # Ensure this is correct. If it's a public channel, use '@channelname'.
COINMARKETCAP_API_KEY = os.getenv('COINMARKETCAP_API_KEY')  # API Key for CoinMarketCap


# Convert CHANNEL_IDENTIFIER to integer if it is numeric, otherwise leave as is
try:
    channel_id = int(CHANNEL_IDENTIFIER)
except ValueError:
    channel_id = CHANNEL_IDENTIFIER
    
# Initialize the Telegram client
client = TelegramClient('bot_session', TELEGRAM_API_ID, TELEGRAM_API_HASH).start(bot_token=BOT_TOKEN)


def get_token_usd_price(token_id):
    url = f"https://alcor.exchange/api/v2/tokens/{token_id}"
    response = requests.get(url)
    data = response.json()
    return data['usd_price']


def convert_currency(api_key, amount, from_symbol, to_symbol):
    url = "https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
    parameters = {'amount': amount, 'symbol': from_symbol, 'convert': to_symbol}
    headers = {'Accepts': 'application/json', 'X-CMC_PRO_API_KEY': api_key}

    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()
    price = data['data'][0]['quote'][to_symbol]['price']
    return price

def calculate_frogs(value_usd, scale=1, max_per_line=12):
    # Start with one line of 12 frog emojis
    frogs = '🐸' * max_per_line + '\n'

    # Calculate additional frogs based on the value
    num_frogs = int(value_usd // scale)  # Calculate number of additional frogs

    while num_frogs > 0:
        line_length = min(num_frogs, max_per_line)
        frogs += '🐸' * line_length + '\n'
        num_frogs -= line_length

    return frogs.strip()  # Remove trailing newline


async def process_and_send(data):
    logger.info("Starting to process and send data")
    try:
        unique_trx_ids = set()

        items_data = data.get('@data', {})
        if not items_data:
            logger.error(f"'@data' key not found or empty in data: {data}")
            return

        items = items_data.get('items', [])
        if not items:
            logger.error("No 'items' found to process in '@data'.")
            return

        image_path = r'C:\Users\sammc\tg-bots\tg-bot-telethon\kek.png'
        image = await client.upload_file(image_path)

        for item in items:
            trx_id = item.get('trxId')
            if trx_id in unique_trx_ids:
                continue

            logger.info(f"Processing item: {item}")
            unique_trx_ids.add(trx_id)
            from_address = item.get('from')
            quantity_str = item.get('quantity', '0 WAX')
            quantity = float(quantity_str.split()[0]) if quantity_str else 0

            wax_usd_value = convert_currency(COINMARKETCAP_API_KEY, quantity, 'WAXP', 'USDT')
            wax_usd_value_formatted = f"${wax_usd_value:.2f}"

                        # Use the function to determine the frog emojis
            frogs = calculate_frogs(wax_usd_value)

            memo_parts = item.get('memo', '').split('#')
            memo_amount = memo_parts[3].split('@')[0] if len(memo_parts) > 3 else 'N/A'

            short_trx_id = trx_id[:7] + "…"  # Truncate the trx_id and append ellipsis

            tlm_usd_price = get_token_usd_price('tlm-alien.worlds')
            market_cap = total_supply * tlm_usd_price
            market_cap_formatted = f"{market_cap:,.2f}"  # Format with commas and two decimal places


            message = (
                f"**$KEK** BUY!!!\n"
                f"{frogs}\n\n"  # Display the dynamic number of frog emojis
                f"🙋‍♂️ {from_address}\n"
                f"💵 {quantity} WAX ({wax_usd_value_formatted})\n"
                f"🪙 {memo_amount}\n"
                f"[⛓️ {short_trx_id}](https://waxblock.io/transaction/{trx_id}) | Txn\n"
                f"🧢 Market Cap: **${market_cap_formatted}**\n\n\n"
                f"📈 [Chart](https://alcor.exchange/trade/tlm-alien.worlds_wax-eosio.token) | "
                f"🤝 [Trade](https://alcor.exchange/swap?input=WAX-eosio.token&output=TLM-alien.worlds)\n"
                f"Made with 💚 by Wax Pepe"
            )
            
            logger.info(f"Preparing to send message: {message}")
            await client.send_file(channel_id, image, caption=message)
            logger.info(f"Message sent to {channel_id}: {message}")

    except Exception as e:
        logger.error(f"Error in process_and_send: {e}")


# Paths
image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kek.png')
SPKG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'antelope-tokens-v0.3.1.spkg')

async def stream_transactions():
    try:
        # Ensure the client is connected
        if not client.is_connected:
            await client.connect()

        cmd = [
            'substreams', 'run', '-e', 'wax.substreams.pinax.network:443',
            SPKG_PATH, 'map_transfers', '-s', '-10', '-o', 'json'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, shell=True)

        json_buffer = ""
        brace_count = 0

        while True:
            line = process.stdout.readline()
            if not line:
                break

            if '{' in line:
                brace_count += line.count('{')
            
            if brace_count > 0:
                json_buffer += line.rstrip()

            if '}' in line:
                brace_count -= line.count('}')

            if brace_count == 0 and json_buffer:
                try:
                    data = json.loads(json_buffer)
                    logger.info(f"JSON data parsed successfully: {data}")  # Log the parsed data for verification
                    await process_and_send(data)
                    json_buffer = ""  # Reset the buffer for the next JSON object
                except json.JSONDecodeError as e:
                    logger.error("JSON decoding error: %s for buffer: %s", e, json_buffer)
                    json_buffer = ""  # Clear the buffer to start fresh for the next JSON object

    except Exception as e:
        logger.error("Error in stream_transactions: %s", e)

async def main():
    try:
        logger.info("Bot starting...")
        await client.start()
        logger.info("Bot started")
        await stream_transactions()
    except Exception as e:
        logger.error(f"Error in main: {e}")
    finally:
        await client.run_until_disconnected()
        logger.info("Bot stopped")

# Run the bot
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
