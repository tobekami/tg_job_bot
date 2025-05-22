import csv
from telethon.sync import TelegramClient
from telethon.tl.types import Channel, Chat

# Your credentials
api_id = 28050501
api_hash = '006f0985fdf2cd5e810a5373254244ff'
session_name = 'group_fetcher'
output_file = 'data/groups.csv'

with TelegramClient(session_name, api_id, api_hash) as client:
    dialogs = client.get_dialogs()

    group_data = []

    for dialog in dialogs:
        entity = dialog.entity

        if isinstance(entity, (Channel, Chat)):
            # Catch both mega groups (supergroups) and normal groups
            is_group = getattr(entity, 'megagroup', False) or isinstance(entity, Chat)
            if is_group:
                group_id = entity.id
                full_id = f"-100{group_id}" if isinstance(entity, Channel) else str(group_id)
                group_data.append({
                    'Group Name': entity.title,
                    'Username': getattr(entity, 'username', ''),
                    'Group ID': full_id
                })
                print(f"✅ Found group: {entity.title} | ID: {full_id} | Username: {getattr(entity, 'username', 'None')}")

    # Save to CSV
    with open(output_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Group Name', 'Username', 'Group ID'])
        writer.writeheader()
        writer.writerows(group_data)

    print(f"\n📁 Group info saved to {output_file}")
