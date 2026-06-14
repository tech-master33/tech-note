import os

TECH_SOFT = os.path.join(os.environ.get('USERPROFILE', os.path.expanduser('~')), '.tech-soft')
ACCOUNT_PATH = os.path.join(TECH_SOFT, 'account.json')
SETTINGS_PATH = os.path.join(TECH_SOFT, 'settings.json')
