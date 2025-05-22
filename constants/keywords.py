from telethon.tl.types import PeerChat

# Group IDs to monitor
PRIVATE_GROUP_ID = PeerChat(4760383950)
GROUPS = [
    PRIVATE_GROUP_ID,   # Private group
    # -1002579059359 #-1001854701169, -1001891392293, -1001952636329, -1001952636329, -1001971671774  Example public group (replace with real ID or username)
]
employer_keywords = [
    "we are", "we're hiring", "we are looking for", "need a", "job opening",
    "join our team", "now hiring", "open position", "apply now", "work with us",
    "seeking", "vacancy", "opportunity", "positions available", "recruiting",
    "join us", "immediate hire", "urgently hiring", "hiring now", "currently need someone",
    "we need someone", "must have", "requirements", "responsibilities", "what we offer",
    "compensation", "salary", "commission", "shift available", "to apply", "fill out this form",
    "dm to apply", "send resume", "submit application", "work opportunity", "required"
]

freelancer_keywords = [
    "available", "freelancer", "hire me", "looking for work", "ready to work",
    "seeking job", "open to opportunities", "i can work", "i'm experienced in", "my skills",
    "i offer", "services", "portfolio", "proof of work", "i specialize in",
    "i have experience", "willing to learn", "can start immediately", "flexible schedule",
    "full-time", "part-time", "remote work", "open for collaboration", "let’s connect",
    "let’s discuss", "i’m interested", "need a job", "job seeker", "available for hire",
    "i’m searching for", "let me help", "i’m a", "i’m from", "my rate is", "interested in hiring", "i'm an expert",
    "i'm experienced"
]

barred_keywords = [
    "sent a dm", "hack", "unban", "unbans", "can't send message", "can't dm", "automates", "automate", "buying",
    "hackers", "limited spot", "limited spots", "needs traffic", "banned", "removal", "limited space", "spanish",
    "french", "danish", "swap", "recovery"
]

GROUP_MESSAGE_INTERVAL = 60  # Time between full rounds (e.g., 1 hour)
PER_GROUP_DELAY = 10
