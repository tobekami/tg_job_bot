import random
from pathlib import Path

DATA_DIR = Path('data')

class PitchManager:
    def __init__(self, group_file=DATA_DIR / 'pitches.txt', private_file=DATA_DIR / 'private_pitches.txt'):
        self.group_file = group_file
        self.private_file = private_file
        self.group_pitches = []
        self.private_pitches = []
        self.load_pitches()

    def load_pitches(self):
        self.group_pitches = self._load_file(self.group_file)
        self.private_pitches = self._load_file(self.private_file)

    def _load_file(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return [p.strip() for p in f.read().split('---') if p.strip()]
        except Exception as e:
            print(f"⚠️ Could not load {path.name}: {e}")
            return []

    def get_random_group_pitch(self):
        return random.choice(self.group_pitches) if self.group_pitches else "👋 Freelance available!"

    def get_random_private_pitch(self):
        return random.choice(self.private_pitches) if self.private_pitches else "Hi, are you looking for help?"
