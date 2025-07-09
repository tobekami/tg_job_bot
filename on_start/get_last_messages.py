import asyncio
import json
import datetime
import random

from telethon.tl.types import PeerChat
from pathlib import Path
from classifier.keyword_classifier import label_message_keywords
from classifier.llm_classifier import classify_message_llm
from classifier.model_classifier import classify_message_model
from constants.keywords import GROUPS, PRIVATE_GROUP_ID
from managers.contact_manager import ContactManager
from managers.pitch_manager import PitchManager


contact_manager = ContactManager()
pitch_manager = PitchManager()

DATA_DIR = Path('data')
LAST_READ_FILE = DATA_DIR / 'last_read.json'


def load_last_read():
    try:
        with open(LAST_READ_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_last_read(data):
    with open(LAST_READ_FILE, 'w') as f:
        json.dump(data, f, indent=2)


async def process_missed_messages(client, last_read):
    now = datetime.datetime.now(datetime.timezone.utc)

    for group in GROUPS:
        # Extract chat_id and force it negative for consistency
        if isinstance(group, PeerChat):
            group_id = -abs(group.chat_id)  # Ensure negative
        else:
            group_id = group  # Already a raw ID, maybe already negative

        group_id_str = str(group_id)

        print(f"🔍 Checking missed messages in group {group_id_str}")

        last_time_str = last_read.get(group_id_str)
        if not last_time_str:
            print(f"🕒 No previous timestamp for group {group_id}. Skipping...")
            continue

        last_time = datetime.datetime.fromisoformat(last_time_str)  # stored_time from file

        if now - last_time > datetime.timedelta(hours=12):
            print(f"⏱️ Last message was more than 12h ago for group {group_id}. Skipping...")
            continue

        me = await client.get_me()
        my_id = me.id

        try:
            found = False
            buffered_time = last_time - datetime.timedelta(seconds=10)

            print(now - last_time)
            print(f"⏰ Stored last read time for group {group_id}: {last_time.isoformat()}")
            print(f"🔄 Using buffered_time: {buffered_time.isoformat()}")

            async for message in client.iter_messages(
                    group,
                    offset_date=buffered_time,
                    reverse=True  # crucial: get messages from oldest to newest
            ):
                msg_time = message.date
                if msg_time.tzinfo is None:
                    msg_time = msg_time.replace(tzinfo=datetime.timezone.utc)

                text = message.message or ""  # Preview
                safe_text = text.replace('\n', ' ')[:60]

                sender = await message.get_sender()
                sender_id = sender.id

                # Skip own messages
                if sender_id == my_id:
                    print(f"🙅 Skipping own message {message.id}")
                    continue

                print(f"📨 Message ID {message.id} | From: {sender_id} | Date: {msg_time.isoformat()} | Text: {safe_text}")

                if msg_time <= last_time:
                    print(
                        f"⏭️ Skipping message {message.id}: message.date ({msg_time.isoformat()}) <= last_time ({last_time.isoformat()})")
                    continue

                found = True
                # ✅ Skip classification if we've already messaged this user
                if sender_id in contact_manager.messaged_users or sender_id in contact_manager.processing_users:
                    print(f"⏩ Already messaged or processing {sender_id}, skipping...")
                    return


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
                            reply_to=message.id
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

                        group_id = str(group)
                        last_read[group_id] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                        save_last_read(last_read)
                        contact_manager.save_to_disk()

                    except Exception as e:
                        print(f"⚠️ Failed to message {sender_id}: {e}")

                    contact_manager.add_messaged_user(sender_id)

                    name = user_info['username'] or user_info['full_name']
                    print(f"💬 [Replay] Messaged: {name} (ID: {sender_id})")

                    # Update last read timestamp
                    last_read[group_id] = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    save_last_read(last_read)

            if not found:
                print(f"📭 No new messages found in group {group_id} since {last_time.isoformat()}")

        except Exception as e:
            print(f"❌ Failed replaying group {group_id}: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()


