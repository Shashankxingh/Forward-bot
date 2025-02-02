import os
from telethon import TelegramClient, events
import asyncio
import logging
import time
from collections import defaultdict

# Configure logging
logging.basicConfig(
    filename="telegram_forwarder.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# Owner information
owner_username = "shashankxingh"
owner_id = 7563434309

# Load API credentials from environment variables
api_id_1 = os.getenv('API_ID_1')  # Environment variable for API ID 1
api_hash_1 = os.getenv('API_HASH_1')  # Environment variable for API Hash 1
phone_1 = os.getenv('PHONE_1')  # Environment variable for phone number 1

api_id_2 = os.getenv('API_ID_2')  # Environment variable for API ID 2
api_hash_2 = os.getenv('API_HASH_2')  # Environment variable for API Hash 2
phone_2 = os.getenv('PHONE_2')  # Environment variable for phone number 2

# Initialize both Telegram clients
client1 = TelegramClient('client1', api_id_1, api_hash_1)
client2 = TelegramClient('client2', api_id_2, api_hash_2)

allowed_users_file = "allowed_users.json"
allowed_users = defaultdict(set)
client1_owner = None  

def load_allowed_users():
    global allowed_users
    try:
        with open(allowed_users_file, "r") as file:
            data = json.load(file)
            allowed_users = defaultdict(set, {int(k): set(v) for k, v in data.items()})
            logging.info("Allowed users loaded successfully.")
    except FileNotFoundError:
        logging.warning("Allowed users file not found. Starting fresh.")
    except Exception as e:
        logging.error(f"Error loading allowed users: {e}")

def save_allowed_users():
    try:
        with open(allowed_users_file, "w") as file:
            json.dump({str(k): list(v) for k, v in allowed_users.items()}, file)
            logging.info("Allowed users saved successfully.")
    except Exception as e:
        logging.error(f"Error saving allowed users: {e}")

async def get_ping(client, chat_id):
    try:
        start_time = time.time()
        msg = await client.send_message(chat_id, "Pinging...")
        end_time = time.time()
        ping = round((end_time - start_time) * 1000, 2)  
        await msg.delete()  
        return ping
    except Exception as e:
        logging.error(f"Error calculating ping: {e}")
        return "Error"

async def main():
    global allowed_users, client1_owner

    load_allowed_users()

    try:
        await client1.start(phone_1)
        await client2.start(phone_2)

        client1_me = await client1.get_me()
        client1_owner = client1_me.username  
        logging.info(f"Client 1 owner: @{client1_owner}")
        print(f"Client 1 owner: @{client1_owner}")

        logging.info("Both clients started successfully!")
        print("Both clients are running!")

        # Ping command to check ping in ms
        @client1.on(events.NewMessage(pattern=r'^\!ping$'))
        async def ping(event):
            chat_id = event.chat_id
            if event.sender_id == owner_id or str(event.sender_id) in allowed_users[chat_id]:
                ping = await get_ping(client2, chat_id)
                await client2.send_message(chat_id, f"Ping: {ping} ms")
            else:
                await client2.send_message(chat_id, "You are not authorized to check the ping.")
            await event.delete()

        # Add user command
        @client1.on(events.NewMessage(pattern=r'^\.add$'))
        async def add_user(event):
            chat_id = event.chat_id
            if event.is_reply:
                replied_message = await event.get_reply_message()
                user_id = replied_message.sender_id
                username = replied_message.sender.username
                user_link = f"[User](tg://user?id={user_id})" if not username else f"@{username}"

                if event.sender_id == owner_id:  # Check if it's the owner adding
                    if str(user_id) not in allowed_users[chat_id]:
                        allowed_users[chat_id].add(str(user_id))
                        save_allowed_users()
                        await client2.send_message(event.chat_id, f"{user_link} has been approved.")
                        logging.info(f"User {user_link} added.")
                    else:
                        await client2.send_message(event.chat_id, f"{user_link} is already allowed.")
                else:
                    await client2.send_message(event.chat_id, "You are not authorized to add users.")
            else:
                await client2.send_message(event.chat_id, "Reply to a user with `.add` to allow them.")
            await event.delete()

        # List allowed users command
        @client1.on(events.NewMessage(pattern=r'^\.user$'))
        async def list_allowed_users(event):
            chat_id = event.chat_id
            sender = await event.get_sender()
            sender_id = sender.id

            if event.sender_id == owner_id:  # Allow owner to view list
                if allowed_users[chat_id]:  # Check if there are any allowed users
                    user_list = []
                    for user_id in allowed_users[chat_id]:
                        try:
                            user = await client2.get_entity(int(user_id))  # Get user entity to fetch first name
                            # Use first name and create a clickable link to their ID
                            user_link = f"[{user.first_name}](tg://user?id={user.id})"
                            user_list.append(user_link)
                        except Exception as e:
                            logging.error(f"Error fetching user data for {user_id}: {e}")
                    
                    # Send the list of users
                    await client2.send_message(event.chat_id, f"Allowed users:\n" + "\n".join(user_list))
                else:
                    await client2.send_message(event.chat_id, "No allowed users.")
            else:
                await client2.send_message(event.chat_id, "You do not have permission to view the list.")
            
            await event.delete()

        # Remove user command
        @client1.on(events.NewMessage(pattern=r'^\.rem$'))
        async def remove_user(event):
            chat_id = event.chat_id
            if event.is_reply:
                replied_message = await event.get_reply_message()
                user_id = replied_message.sender_id
                username = replied_message.sender.username
                user_link = f"[User](tg://user?id={user_id})" if not username else f"@{username}"

                if event.sender_id == owner_id:  # Allow owner to remove users
                    if str(user_id) in allowed_users[chat_id]:
                        allowed_users[chat_id].remove(str(user_id))
                        save_allowed_users()
                        await client2.send_message(event.chat_id, f"{user_link} has been removed.")
                    else:
                        await client2.send_message(event.chat_id, f"{user_link} is not in the allowed list.")
                else:
                    await client2.send_message(event.chat_id, "You are not authorized to remove users.")
            else:
                await client2.send_message(event.chat_id, "Reply to a user with `.rem` to remove them.")
            await event.delete()

        # Handle all other messages
        @client1.on(events.NewMessage(pattern=r'^\.(?!ping|add|user|rem).+'))
        async def handle_message(event):
            print(f"Sender ID: {event.sender_id}")  # Debugging print
            if event.sender_id == owner_id:  # Owner bypass check
                new_message = event.text[1:]
                await client2.send_message(event.chat_id, new_message, reply_to=event.reply_to_msg_id)
                await event.delete()
                await asyncio.sleep(3)
            elif str(event.sender_id) in allowed_users[event.chat_id]:  # Regular user check
                new_message = event.text[1:]
                await client2.send_message(event.chat_id, new_message, reply_to=event.reply_to_msg_id)
                await event.delete()
                await asyncio.sleep(3)
            else:
                await client2.send_message(event.chat_id, "You are not allowed to use this bot.")

        print("Listening for messages...")
        await asyncio.gather(client1.run_until_disconnected(), client2.run_until_disconnected())

    except Exception as e:
        logging.error(f"Error in main: {e}")
        print(f"Error in main: {e}")

while True:
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Bot crashed: {e}")
        time.sleep(5)