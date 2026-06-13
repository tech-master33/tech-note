import datetime

def tell_time(assistant, command=None):
    now = datetime.datetime.now()
    hour = now.strftime("%I").lstrip("0") or "12"
    minute = now.strftime("%M")
    ampm = now.strftime("%p")
    assistant.speak(f"{assistant.username}, the time is {hour}:{minute} {ampm}.")

def tell_date(assistant, command=None):
    now = datetime.datetime.now()
    assistant.speak(f"Today is {now.strftime('%A, %B %d, %Y')}.")
