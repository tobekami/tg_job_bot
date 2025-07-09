import datetime
import random

from telethon import TelegramClient, events
from managers.contact_manager import ContactManager
from managers.pitch_manager import PitchManager
from classifier.keyword_classifier import label_message_keywords
from classifier.model_classifier import classify_message_model
from classifier.llm_classifier import classify_message_llm
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
    now = datetime.datetime.now(datetime.timezone.utc)

    # Parse last group message timestamp if it exists
    last_group_message_str = last_read.get("last_group_message")
    last_group_message = (
        datetime.datetime.fromisoformat(last_group_message_str)
        if last_group_message_str else None
    )

    # ⏪ Recover missed messages before starting listeners
    await process_missed_messages(client, last_read)

    async def periodic_group_message():
        nonlocal last_group_message  # So we can update it inside this function
        now = datetime.datetime.now(datetime.timezone.utc)

        if not last_group_message or (now - last_group_message) > datetime.timedelta(hours=24):
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
                    print(f"❌ Failed to send group message to {group}: {e}")

                await asyncio.sleep(PER_GROUP_DELAY)

            # ✅ Update last_group_message timestamp
            last_group_message = datetime.datetime.now(datetime.timezone.utc)
            last_read["last_group_message"] = last_group_message.isoformat()
            save_last_read(last_read)

        elif (now - last_group_message) < datetime.timedelta(hours=24):
            print(f"🕒 Last group message was less than 24 hours ago. Skipping...")

    async def periodic_group_message_loop():
        while True:
            await periodic_group_message()
            await asyncio.sleep(3600)  # Wait 1 hour before next round

    @client.on(events.NewMessage(chats=GROUPS))
    async def keyword_listener(event):
        sender = await event.get_sender()
        sender_id = sender.id

        # ✅ Skip classification if we've already messaged this user
        if sender_id in contact_manager.messaged_users or sender_id in contact_manager.processing_users:
            print(f"⏩ Already messaged or processing {sender_id}, skipping...")
            return

        contact_manager.processing_users.add(sender_id)

        text = event.message.message

        # Step 1: Keyword classification
        label = label_message_keywords(text)
        print(f"🔍 Keyword-based label: {label}")

        # Step 2: Model fallback if unsure
        if label == 'unsure':
            label = classify_message_model(text)
            print(f"🤖 Model-based label: {label}")

        # Step 3: Use LLM only for employer messages
        if label == 'employer':
            llm_result = await classify_message_llm(text)
            confirmed_label = llm_result.get("label")
            reason = llm_result.get("reason", "No reason provided")
            response = llm_result.get("response", "No response provided")

            if confirmed_label != 'employer':
                print(
                    f"❌ LLM disagreed. Ignoring message. LLM said: {confirmed_label} | Reason: {reason}"
                )
                return

            print(f"✅ LLM confirmed employer message: {reason}")
            print(f"💼 Detected employer message from {sender_id}: {text[:60]}...")

            try:
                user_info = await contact_manager.get_or_cache_user(client, sender_id, sender)
                if not user_info:
                    print(f"⚠️ Could not get contact info for {sender_id} — will try to send message anyway.")
                else:
                    print(f"✅ Got user info for {sender_id}: {user_info}")

                await asyncio.sleep(random.randint(5, 15))  # Human-like delay

                await client.send_message(
                    sender_id,
                    response,
                    reply_to=event.message.id
                )

                await asyncio.sleep(random.randint(2, 3))  # Human-like delay

                await client.send_message(
                    PRIVATE_GROUP_ID,
                    f'📢 You just texted [this employer](tg://user?id={sender_id}) regarding a job.\n\nMessage: "{text}"',
                    parse_mode='markdown'
                )

                contact_manager.add_messaged_user(sender_id)
                name = user_info['username'] or user_info['full_name']
                contact_manager.processing_users.discard(sender_id)
                print(f"💬 Messaged: {name} (ID: {sender_id})")

                group_id = str(event.chat_id)
                last_read[group_id] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                save_last_read(last_read)
                contact_manager.save_to_disk()

            except Exception as e:
                print(f"⚠️ Failed to message {sender_id}: {e}")
                await client.send_message(
                    PRIVATE_GROUP_ID,
                    f'📢 You just tried to text [this employer](tg://user?id={sender_id}) regarding a job, but failed.\n\nMessage: "{text}"',
                    parse_mode='markdown'
                )
                contact_manager.processing_users.discard(sender_id)

    try:
        await asyncio.gather(
            periodic_group_message_loop(),
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
