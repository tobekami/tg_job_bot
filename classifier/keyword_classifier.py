from constants.keywords import employer_keywords, freelancer_keywords, barred_keywords


def label_message_keywords(text):
    text = text.lower()
    if any(b in text for b in barred_keywords):
        return 'barred'

    employer_count = sum(1 for k in employer_keywords if k in text)
    freelancer_count = sum(1 for k in freelancer_keywords if k in text)

    if employer_count >= 2 and employer_count > freelancer_count:
        return 'employer'
    elif freelancer_count >= 2 and freelancer_count > employer_count:
        return 'freelancer'
    return 'unsure'
