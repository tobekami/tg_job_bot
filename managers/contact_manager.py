import csv
import time
from pathlib import Path

DATA_DIR = Path('data')
CONTACTS_CSV = DATA_DIR / 'contacts.csv'
MESSAGED_USERS_CSV = DATA_DIR / 'messaged_users.csv'

class ContactManager:
    def __init__(self):
        self.contact_cache = {}
        self.messaged_users = set()
        DATA_DIR.mkdir(exist_ok=True)
        self.load_from_disk()

    def load_from_disk(self):
        try:
            if CONTACTS_CSV.exists():
                with open(CONTACTS_CSV, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.contact_cache[int(row['user_id'])] = {
                            'username': row['username'],
                            'full_name': row['full_name'],
                            'timestamp': float(row['timestamp'])
                        }

            if MESSAGED_USERS_CSV.exists():
                with open(MESSAGED_USERS_CSV, 'r', encoding='utf-8') as f:
                    self.messaged_users = {int(row[0]) for row in csv.reader(f)}

            print("✅ Loaded contact data")
        except Exception as e:
            print(f"⚠️ Error loading contact data: {e}")

    def save_to_disk(self):
        try:
            with open(CONTACTS_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['user_id', 'username', 'full_name', 'timestamp'])
                writer.writeheader()
                for uid, info in self.contact_cache.items():
                    writer.writerow({'user_id': uid, **info})

            with open(MESSAGED_USERS_CSV, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                for uid in self.messaged_users:
                    writer.writerow([uid])
        except Exception as e:
            print(f"⚠️ Error saving contact data: {e}")

    async def get_or_cache_user(self, client, user_id):
        if user_id in self.contact_cache and time.time() - self.contact_cache[user_id]["timestamp"] < 3600:
            return self.contact_cache[user_id]
        try:
            user = await client.get_entity(user_id)
            self.contact_cache[user_id] = {
                'username': user.username,
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'timestamp': time.time()
            }
            self.save_to_disk()
            return self.contact_cache[user_id]
        except Exception as e:
            print(f"⚠️ Could not fetch user {user_id}: {e}")
            return None

    def add_messaged_user(self, user_id):
        self.messaged_users.add(user_id)
        self.save_to_disk()
