import os
import json
import time
import asyncio
import requests
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from pyrogram import Client, filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import Timeout, UserIsBlocked
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from requests.packages.urllib3.exceptions import InsecureRequestWarning

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))
ADMIN_IDS = [7456660566]

COUNTER_FILE = "user_counter.txt"
SMSYNE_OPERATOR = "5"
SMSYNE_COUNTRY_NAME = "India"
SMSYNE_SERVICE_ID = "abl"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


active_loops = {}

app = Client(
    "registration_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

BASE_URL = "https://api.smsyne.com/stubs/handler_api.php"
def make_api_request(params):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=30, verify=False)
        response.raise_for_status()
        try: return response.json()
        except json.JSONDecodeError: return response.text
    except requests.exceptions.RequestException as e:
        return {"error": f"API Request Failed", "details": str(e)}
def get_balance(api_key): return make_api_request({"api_key": api_key, "action": "getBalance"})
def get_countries(api_key, operator): return make_api_request({"api_key": api_key, "action": "getCountries", "operator": operator})
def get_number(api_key, service, country, operator): return make_api_request({"api_key": api_key, "action": "getNumber", "service": service, "country": country, "operator": operator})
def get_status(api_key, order_id): return make_api_request({"api_key": api_key, "action": "getStatus", "id": order_id})
def set_status(api_key, order_id, status_code): return make_api_request({"api_key": api_key, "action": "setStatus", "id": order_id, "status": status_code})
def find_key_by_value(data_dict, value_to_find):
    if not isinstance(data_dict, dict): return None
    for key, value in data_dict.items():
        if str(value).lower() == str(value_to_find).lower(): return key
    return None

def get_session_with_csrf(url="https://playkaro365.com/join-now"):
    print("Initializing Selenium to fetch session data...")
    options = Options()
    options.add_argument("--headless=new"); options.add_argument("--disable-gpu"); options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage"); options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled"); options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-infobars"); options.add_argument(f"user-agent={USER_AGENT}")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        driver.get(url); time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        token_tag = soup.find("meta", {"name": "csrf-token"})
        if not token_tag: print("Error: CSRF Token meta tag not found."); return None, None

        csrf_token = token_tag.get('content')
        selenium_cookies = driver.get_cookies()
        if not csrf_token or not selenium_cookies: print("Error: Failed to extract CSRF token or cookies."); return None, None

        session = requests.Session()
        for cookie in selenium_cookies: session.cookies.set(cookie['name'], cookie['value'], domain=cookie.get('domain'))
        print(f"Successfully obtained CSRF Token: {csrf_token[:10]}... and session cookies.")
        return session, csrf_token
    except Exception as e:
        print(f"A critical error occurred during Selenium initialization: {e}"); return None, None
    finally:
        if driver: driver.quit(); print("Selenium driver has been closed.")

def get_current_username_index() -> int:
    try:
        with open(COUNTER_FILE, "r") as f: return int(f.read().strip())
    except (FileNotFoundError, ValueError): return 1
def set_counter_value(value: int):
    with open(COUNTER_FILE, "w") as f: f.write(str(value))
def increment_username_index(current_index: int):
    set_counter_value(current_index + 1)

@app.on_message(filters.command("start") & filters.private)
async def start_command_handler(client: Client, message: Message):
    chat_id, user_id = message.chat.id, message.from_user.id
    if active_loops.get(chat_id): await message.reply_text("⚠️ **A process is already running!**\nType /cancel to stop it."); return
    if user_id in ADMIN_IDS:
        await message.reply_text("👋 **Admin Menu**\nChoose a mode:", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 Start Automatic Creation", callback_data="start_auto")],
            [InlineKeyboardButton("👨‍💻 Start Manual Registration", callback_data="start_manual")]
        ]))
    else: await message.reply_text("👋 **Welcome!**")

@app.on_message(filters.command("cancel") & filters.private)
async def cancel_command_handler(client: Client, message: Message):
    chat_id = message.chat.id
    if active_loops.get(chat_id):
        active_loops[chat_id] = False; await message.reply_text("✅ **Cancellation Signal Received!**")
    else: await message.reply_text("ℹ️ No active process to cancel.")

@app.on_message(filters.command("setcounter") & filters.private & filters.user(ADMIN_IDS))
async def set_counter_handler(client: Client, message: Message):
    try:
        new_value = int(message.text.split(maxsplit=1)[1])
        set_counter_value(new_value); await message.reply_text(f"✅ Counter set. Next: `Harishk{new_value}`.")
    except (IndexError, ValueError): await message.reply_text("⚠️ Usage: `/setcounter <number>`")

@app.on_message(filters.command("getcounter") & filters.private & filters.user(ADMIN_IDS))
async def get_counter_handler(client: Client, message: Message):
    await message.reply_text(f"ℹ️ Next username: `Harishk{get_current_username_index()}`.")

@app.on_message(filters.command("balance") & filters.private & filters.user(ADMIN_IDS))
async def balance_handler(client: Client, message: Message):
    """Checks and displays the SMSYNE API balance, handling the API's specific response format."""
    api_key = os.getenv("SMSYNE_API_KEY")
    if not api_key:
        await message.reply_text("❌ **API Key Not Found!**\nEnsure `SMSYNE_API_KEY` is set in your environment.")
        return

    msg = await message.reply_text("⏳ Checking your SMSYNE balance...")

    balance_response = await asyncio.to_thread(get_balance, api_key)

    if isinstance(balance_response, dict) and "error" in balance_response:

        await msg.edit(f"❌ **API Request Failed!**\nDetails: `{balance_response['details']}`")
        return


    if isinstance(balance_response, str) and balance_response.startswith("ACCESS_BALANCE:"):
        try:

            balance_value = balance_response.split(':')[1]
            await msg.edit(f"💰 **Your SMSYNE Balance:**\n\n`{balance_value}`")
        except IndexError:

            await msg.edit(f"⚠️ **API Parsing Error!**\nCould not parse a valid balance from the response: `{balance_response}`")
    else:

        await msg.edit(f"⚠️ **API Error!**\nServer response: `{balance_response}`")


@app.on_callback_query(filters.regex("start_manual"))
async def manual_registration_handler(client: Client, callback_query):
    chat_id = callback_query.message.chat.id; await callback_query.message.delete()
    if active_loops.get(chat_id): await client.send_message(chat_id, "Process already running. /cancel first."); return
    active_loops[chat_id] = True; await run_manual_registration(client, chat_id)

@app.on_callback_query(filters.regex("start_auto"))
async def auto_creation_prompt(client: Client, callback_query):
    chat_id = callback_query.message.chat.id; await callback_query.message.delete()
    if active_loops.get(chat_id): await client.send_message(chat_id, "Process already running. /cancel first."); return
    ask_msg = await client.send_message(chat_id, "How many accounts to create automatically?")
    try:
        response = await client.listen(chat_id, timeout=60); await ask_msg.delete()
        if response.text == "/cancel": await response.reply_text("✅ Operation cancelled."); return
        count = int(response.text); await response.delete()
        if count <= 0: await client.send_message(chat_id, "❌ Please enter a positive number."); return
        active_loops[chat_id] = True; await run_automatic_creation(client, chat_id, count)
    except Timeout: await ask_msg.edit("⏰ Timeout. Please start over.")
    except (ValueError, TypeError): await client.send_message(chat_id, "❌ Invalid input. Please enter a number.")
    finally: active_loops.pop(chat_id, None)


async def run_manual_registration(client: Client, chat_id: int):
    last_msg = await client.send_message(chat_id, "🚀 **Manual registration process started!**")

    while active_loops.get(chat_id):
        try:
            current_index = get_current_username_index()
            username = f"Gtmrh{current_index}"
            email, password = f"{username}@gmail.com", "pa1@P"

            # <<< MODIFICATION: Initialize session first >>>
            await last_msg.edit(f"**User: `{username}`**\nStep 1/3: Initializing secure session...")
            session, csrf_token = await asyncio.to_thread(get_session_with_csrf)
            if not session or not csrf_token:
                await last_msg.edit(f"❌ **Website Error**: Failed to get session from Selenium. Retrying..."); await asyncio.sleep(5); continue

            # <<< MODIFICATION: Ask for number after session is ready >>>
            number = None
            while number is None and active_loops.get(chat_id):
                ask_num_msg = await client.send_message(chat_id, f"📱 **Registering `{username}`**\nPlease enter a 10-digit mobile number, or /cancel.")
                try:
                    response = await client.listen(chat_id, timeout=300); await ask_num_msg.delete()
                    if response.text == "/cancel": active_loops[chat_id] = False; await response.reply_text("✅ Cancellation acknowledged."); break
                    num_input = response.text.strip(); await response.delete()
                    if num_input.isdigit() and len(num_input) == 10: number = num_input
                    else: await client.send_message(chat_id, "❌ Invalid format. Please enter a 10-digit number.")
                except Timeout: await client.send_message(chat_id, "⏰ Timeout. Please provide a number."); break

            if not number or not active_loops.get(chat_id): break

            headers = {"User-Agent": USER_AGENT, "X-Requested-With": "XMLHttpRequest", "Referer": "https://playkaro365.com/join-now", "X-CSRF-TOKEN": csrf_token}
            signup_data = {"_token": csrf_token, "user_name": username, "email": email, "password": password, "mobile_number": number}

            await last_msg.edit(f"**User: `{username}`**\nStep 2/3: Sending OTP request...")
            signup_res = session.post("https://playkaro365.com/sign-up", data=signup_data, headers=headers)

            try:
                response_json = signup_res.json()
                status, msg_text = response_json.get('status'), (response_json.get('msg') or response_json.get('message', '')).lower()


                if status in ["error", 0]:
                    if "mobile number" in msg_text:
                        await last_msg.edit(f"❌ Number `{number}` is already in use.\nPlease provide a new number for `{username}`.")
                        continue
                    elif "username" in msg_text or "email" in msg_text:
                        await last_msg.edit(f"⚠️ Username/Email for `{username}` is taken. Trying next...")
                        increment_username_index(current_index)
                        await asyncio.sleep(2)
                        continue
                    else:
                        error_msg = response_json.get('msg', 'Unknown error.')
                        await last_msg.edit(f"❌ Website Error for `{username}`: `{error_msg}`\nRetrying the whole process for this user.")
                        await asyncio.sleep(3)
                        continue
            except json.JSONDecodeError:
                await last_msg.edit(f"❌ Website Error for `{username}`\nNon-JSON response for OTP. (Status: {signup_res.status_code}). Retrying...")
                await asyncio.sleep(5); continue

            if not active_loops.get(chat_id): break
            ask_otp_msg = await client.send_message(chat_id, f"🔐 An OTP was sent for `{username}`. Please enter it, or /cancel.")
            otp = None
            try:
                otp_response = await client.listen(chat_id, timeout=300); await ask_otp_msg.delete()
                if otp_response.text == "/cancel": active_loops[chat_id] = False; await otp_response.reply_text("✅ Cancellation acknowledged."); break
                otp = otp_response.text.strip(); await otp_response.delete()
            except Timeout: await last_msg.edit("⏰ OTP Timeout. Restarting with the next user."); continue

            await last_msg.edit(f"**User: `{username}`**\nStep 3/3: Verifying OTP...")
            final_data = {**signup_data, "otp": otp}
            final_res = session.post("https://playkaro365.com/sign-up", data=final_data, headers=headers)

            try:
                final_json = final_res.json()
                if final_json.get("status") in ["success", 1, 205]:
                    success_message = f"✅ **New Account**\n\n👤 **Username:** `{username}`\n🔐 **Password:** `{password}`"
                    await client.send_message(TARGET_CHAT_ID, success_message, parse_mode=enums.ParseMode.MARKDOWN)
                    await last_msg.edit(f"🎉 **`{username}` Registered Successfully!** Moving to the next...")
                    increment_username_index(current_index)
                else:
                    error_msg = final_json.get('msg', 'Unknown finalization error')
                    await last_msg.edit(f"❌ **Registration Failed for `{username}`:** `{error_msg}`\nPlease provide a new number for this user.")
            except json.JSONDecodeError:
                await last_msg.edit(f"❌ Website Error for `{username}`\nNon-JSON on finalization. Retrying.")

            await asyncio.sleep(3)
        except UserIsBlocked: active_loops[chat_id] = False; print(f"User {chat_id} blocked bot."); break
        except Exception as e:
            print(f"Critical error in manual loop for chat {chat_id}: {e}")
            await client.send_message(chat_id, f"🚨 **Critical error:** `{e}`\nRetrying..."); await asyncio.sleep(5)

    await client.send_message(chat_id, "✅ **Manual registration loop has been stopped.**")
    active_loops.pop(chat_id, None)

async def run_automatic_creation(client: Client, chat_id: int, total_accounts: int):
    api_key = os.getenv("SMSYNE_API_KEY");
    if not api_key: await client.send_message(chat_id, "❌ **CRITICAL ERROR:** `SMSYNE_API_KEY` not found."); return

    try:
        country_id = find_key_by_value(get_countries(api_key, SMSYNE_OPERATOR), SMSYNE_COUNTRY_NAME)
        if not country_id: await client.send_message(chat_id, f"❌ **API Error**: Country ID not found."); return
    except Exception as e: await client.send_message(chat_id, f"❌ **API Error**: {e}"); return

    status_msg = await client.send_message(chat_id, f"🚀 **Starting auto-creation of {total_accounts} accounts...**")
    created_count = 0

    for i in range(total_accounts):
        if not active_loops.get(chat_id): await status_msg.edit("🛑 Process cancelled."); break
        await status_msg.edit(f"⚙️ **Progress: {created_count}/{total_accounts}** | Account #{i+1}...")

        order_id, current_index = None, get_current_username_index()
        username = f"Gtmhk{current_index}"
        try:
            email, password = f"{username}@gmail.com", "956683hH"

            # <<< MODIFICATION: Initialize session first >>>
            await status_msg.edit(f"**Progress: {created_count}/{total_accounts} | `{username}`**\nStep 1/5: Initializing session...")
            session, csrf_token = await asyncio.to_thread(get_session_with_csrf)
            if not session or not csrf_token:
                await client.send_message(chat_id, f"❌ **Website Error**: Failed to get session for `{username}`. Retrying.")
                await asyncio.sleep(5); continue

            # <<< MODIFICATION: Get number after session is ready >>>
            await status_msg.edit(f"**Progress: {created_count}/{total_accounts} | `{username}`**\nStep 2/5: Requesting number...")
            number_response = get_number(api_key, SMSYNE_SERVICE_ID, country_id, SMSYNE_OPERATOR)
            if isinstance(number_response, str) and "ACCESS_NUMBER" in number_response:
                order_id, full_phone = number_response.split(':')[1:3]
                phone_to_submit = full_phone[2:] if full_phone.startswith("91") else full_phone
            else:
                await client.send_message(chat_id, f"❌ **SMSYNE Error**: `{number_response}`.")
                await asyncio.sleep(5); continue

            headers = {"User-Agent": USER_AGENT, "X-CSRF-TOKEN": csrf_token, "X-Requested-With": "XMLHttpRequest", "Referer": "https://playkaro365.com/join-now"}
            signup_data = {"_token": csrf_token, "user_name": username, "email": email, "password": password, "mobile_number": phone_to_submit}

            await status_msg.edit(f"**Progress: {created_count}/{total_accounts} | `{username}`**\nStep 3/5: Sending OTP Request...")
            signup_res = session.post("https://playkaro365.com/sign-up", data=signup_data, headers=headers)

            try:
                response_json = signup_res.json()
                status, msg_text = response_json.get('status'), (response_json.get('msg') or response_json.get('message', '')).lower()

                if status in ["error", 0]:
                    set_status(api_key, order_id, 8)
                    if "mobile number" in msg_text:
                        await client.send_message(chat_id, f"❌ Number used by `{username}` is taken. Retrying with a new number.")
                    elif "username" in msg_text or "email" in msg_text:
                        await client.send_message(chat_id, f"⚠️ Username/Email for `{username}` is taken. Trying next username.")
                        increment_username_index(current_index)
                    else:
                        await client.send_message(chat_id, f"❌ Website Error for `{username}`: `{msg_text}`. Retrying with new number.")
                    await asyncio.sleep(3); continue
            except json.JSONDecodeError:
                await client.send_message(chat_id, f"❌ **Website Error for `{username}`**: Non-JSON response on OTP (Status: {signup_res.status_code}). Retrying.");
                set_status(api_key, order_id, 8); await asyncio.sleep(5); continue

            await status_msg.edit(f"**Progress: {created_count}/{total_accounts} | `{username}`**\nStep 4/5: Waiting for OTP...")
            otp, max_wait = None, 300
            for _ in range(max_wait // 10):
                if not active_loops.get(chat_id): break
                status_response = get_status(api_key, order_id)
                if isinstance(status_response, str) and status_response.startswith("STATUS_OK"):
                    otp = status_response.split(':')[1]; break
                await asyncio.sleep(10)
            if not otp:
                if active_loops.get(chat_id): await client.send_message(chat_id, f"❌ **SMSYNE Error for `{username}`**: OTP timeout.")
                set_status(api_key, order_id, 8); continue

            await status_msg.edit(f"**Progress: {created_count}/{total_accounts} | `{username}`**\nStep 5/5: Finalizing...")
            final_data = {**signup_data, "otp": otp}
            final_res = session.post("https://playkaro365.com/sign-up", data=final_data, headers=headers)
            try:
                final_json = final_res.json()
                if final_json.get("status") in ["success", 1, 205]:
                    success_message = f"✅ **New Account (AUTO)**\n\n👤 **Username:** `{username}`\n🔐 **Password:** `{password}`"
                    await client.send_message(TARGET_CHAT_ID, success_message, parse_mode=enums.ParseMode.MARKDOWN)
                    created_count += 1
                    increment_username_index(current_index)
                else:
                    error_msg = final_json.get('msg', 'Finalization failed.')
                    await client.send_message(chat_id, f"❌ **Website Error for `{username}`**: `{error_msg}`. Retrying with new number.")
                    set_status(api_key, order_id, 8)
            except json.JSONDecodeError:
                await client.send_message(chat_id, f"❌ **Website Error for `{username}`**: Non-JSON on finalization (Status: {final_res.status_code}). Retrying.")
                set_status(api_key, order_id, 8)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Critical auto loop error for {username}: {e}"); await client.send_message(chat_id, f"🚨 **Critical error:**\n`{e}`\nRetrying...")
            if order_id: set_status(api_key, order_id, 8)
            await asyncio.sleep(5); continue

    await status_msg.edit(f"✅ **Automatic Creation Finished!**\nCreated **{created_count}** of **{total_accounts}** requested accounts.")
    active_loops.pop(chat_id, None)

if __name__ == "__main__":
    print("Bot is starting with integrated Selenium and enhanced error handling...")
    app.run()
    print("Bot has stopped.")
