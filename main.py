import datetime
import random

from telethon import TelegramClient, events
from managers.contact_manager import ContactManager
from managers.pitch_manager import PitchManager
from classifier.keyword_classifier import label_message_keywords
from classifier.model_classifier import classify_message_model
from constants.keywords import GROUPS, GROUP_MESSAGE_INTERVAL, PER_GROUP_DELAY, PRIVATE_GROUP_ID
from config import api_id, api_hash, session_name
import asyncio
from on_start.get_last_messages import load_last_read, save_last_read, process_missed_messages

client = TelegramClient(session_name, api_id, api_hash)
contact_manager = ContactManager()
pitch_manager = PitchManager()
group_entities = {}


async def main():
    await client.start()
    print("🤖 Listening to group chats...")

    global last_read
    last_read = load_last_read()

    # ⏪ Recover missed messages before starting listeners
    await process_missed_messages(client, last_read)

    async def periodic_group_message():
        while True:
            print("🔁 Starting new broadcast round")
            for group in GROUPS:
                try:
                    group_key = str(group)
                    if group_key not in group_entities:
                        group_entities[group_key] = await client.get_entity(group)

                    await client.send_message(
                        group_entities[group_key],
                        pitch_manager.get_random_group_pitch()
                    )
                    print(f"📣 Sent broadcast to group: {group}")
                except Exception as e:
                    print(f"❌ Failed to send group message: {e}")
                await asyncio.sleep(PER_GROUP_DELAY)
            await asyncio.sleep(GROUP_MESSAGE_INTERVAL)

    @client.on(events.NewMessage(chats=GROUPS))
    async def keyword_listener(event):
        text = event.message.message

        label = label_message_keywords(text)
        print(f"🔍 Keyword-based label: {label}")

        if label == 'unsure':
            label = classify_message_model(text)
            print(f"🤖 Model-based label: {label}")

        if label == 'employer':
            sender = await event.get_sender()
            sender_id = sender.id
            print(f"💼 Detected employer message from {sender_id}: {text[:60]}...")

            try:
                user_info = await contact_manager.get_or_cache_user(client, sender_id)
                if not user_info:
                    print(f"⚠️ Skipping user {sender_id} - no contact info")
                    return

                await asyncio.sleep(random.randint(5, 15))  # Human-like delay

                await client.send_message(
                    sender_id,
                    pitch_manager.get_random_private_pitch(),
                    reply_to=event.message.id
                )

                await asyncio.sleep(random.randint(2, 3))  # Human-like delay

                await client.send_message(
                    PRIVATE_GROUP_ID,
                    f'📢 You just texted [this employer](tg://user?id={sender_id}) regarding a job.\n\nMessage: "{text[:100]}..."',
                    parse_mode='markdown'
                )

                contact_manager.add_messaged_user(sender_id)
                name = user_info['username'] or user_info['full_name']
                print(f"💬 Messaged: {name} (ID: {sender_id})")

                group_id = str(event.chat_id)
                last_read[group_id] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                save_last_read(last_read)
                contact_manager.save_to_disk()
            except Exception as e:
                print(f"⚠️ Failed to message {sender_id}: {e}")

    try:
        await asyncio.gather(
            periodic_group_message(),
            client.run_until_disconnected()
        )
    finally:
        contact_manager.save_to_disk()
        save_last_read(last_read)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    finally:
        print("🧹 Cleaning up...")
