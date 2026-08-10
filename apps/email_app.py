import os
import json
import re
import threading
import win32con
import requests
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT
from core.crypto_util import encrypt, decrypt

EMAIL_CONFIG_PATH = os.path.join(TECH_SOFT, 'email_config.json')
COOKIES_PATH = os.path.join(TECH_SOFT, 'email_cookies.json')

STATE_MENU = 0
STATE_SETUP = 1
STATE_INBOX = 2
STATE_READING = 3
STATE_COMPOSE = 4
STATE_FOLDERS = 5
STATE_SEARCH = 6

PROVIDER_GMAIL = "gmail"
PROVIDER_OUTLOOK = "outlook"

HAS_PLAYWRIGHT = False
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    pass


def _gmail_basic_html_url():
    return "https://mail.google.com/mail/u/0/h/"


class EmailProvider:
    def __init__(self, app):
        self.app = app

    def get_name(self):
        return ""

    def login(self, page, config):
        raise NotImplementedError

    def fetch_inbox(self, page, config):
        raise NotImplementedError

    def read_email(self, page, msg_id):
        raise NotImplementedError

    def send_email(self, page, config, to, subject, body):
        raise NotImplementedError


class GmailProvider(EmailProvider):
    def get_name(self):
        return "Gmail"

    def login(self, page, config):
        basic = _gmail_basic_html_url()
        page.goto(basic)
        if "Sign in" in page.title() or page.url.startswith("https://accounts.google.com"):
            email_input = page.locator('input[type="email"]')
            if email_input.count() > 0:
                email_input.fill(config['email'])
                page.locator('#identifierNext').click()
                page.wait_for_timeout(2000)
                pw_input = page.locator('input[type="password"]')
                if pw_input.count() > 0:
                    pw_input.fill(config['password'])
                    page.locator('#passwordNext').click()
                    page.wait_for_timeout(5000)
            page.wait_for_url("**/h/**", timeout=30000)
        return page

    def fetch_inbox(self, page, config):
        basic = _gmail_basic_html_url()
        page.goto(basic)
        page.wait_for_timeout(2000)
        emails = []
        rows = page.locator('table tbody tr')
        count = min(rows.count(), 20)
        for i in range(count):
            try:
                row = rows.nth(i)
                cells = row.locator('td')
                if cells.count() < 4:
                    continue
                sender = cells.nth(1).inner_text(timeout=1000).strip()
                subject_cell = cells.nth(2)
                subject = subject_cell.inner_text(timeout=1000).strip()
                msg_id = ""
                link = subject_cell.locator('a').first
                if link.count() > 0:
                    href = link.get_attribute('href')
                    if href:
                        m = re.search(r'[&?]q=([^&]+)', href)
                        if m:
                            msg_id = m.group(1)
                emails.append({'sender': sender, 'subject': subject, 'msg_id': msg_id, 'provider': PROVIDER_GMAIL})
            except Exception:
                continue
        return emails

    def read_email(self, page, msg_id):
        basic = _gmail_basic_html_url()
        page.goto(f"{basic}?q={msg_id}")
        page.wait_for_timeout(2000)
        body = ""
        body_div = page.locator('div[style*="font-family"]')
        if body_div.count() > 0:
            body = body_div.first.inner_text()
        if not body:
            pre = page.locator('pre')
            if pre.count() > 0:
                body = pre.first.inner_text()
        return body

    def send_email(self, page, config, to, subject, body):
        basic = _gmail_basic_html_url()
        page.goto(f"{basic}?view=cm&fs=1")
        page.wait_for_timeout(2000)
        to_input = page.locator('input[name="to"]')
        if to_input.count() > 0:
            to_input.fill(to)
        subj_input = page.locator('input[name="subject"]')
        if subj_input.count() > 0:
            subj_input.fill(subject)
        body_area = page.locator('textarea[name="body"]')
        if body_area.count() > 0:
            body_area.fill(body)
        send_btn = page.locator('input[type="submit"][value*="Send"]')
        if send_btn.count() > 0:
            send_btn.click()
            page.wait_for_timeout(3000)


class OutlookProvider(EmailProvider):
    def get_name(self):
        return "Outlook"

    def login(self, page, config):
        page.goto("https://outlook.live.com/mail/0/")
        page.wait_for_timeout(2000)
        signin = page.locator('a[href*="login"]')
        if signin.count() == 0:
            signin = page.locator('[data-task="signin"]')
        if signin.count() > 0:
            signin.first.click()
            page.wait_for_timeout(2000)
        if page.url.startswith("https://login.live.com"):
            email_input = page.locator('input[type="email"]')
            if email_input.count() > 0:
                email_input.fill(config['email'])
                page.locator('input[type="submit"]').first.click()
                page.wait_for_timeout(2000)
                pw_input = page.locator('input[type="password"]')
                if pw_input.count() > 0:
                    pw_input.fill(config['password'])
                    page.locator('input[type="submit"]').first.click()
                    page.wait_for_timeout(5000)
            page.wait_for_url("**/mail/**", timeout=30000)
        return page

    def _cookies_to_session(self, page):
        s = requests.Session()
        for c in page.context.cookies():
            s.cookies.set(c['name'], c['value'], domain=c.get('domain', ''), path=c.get('path', '/'))
        s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        return s

    def fetch_inbox(self, page, config):
        s = self._cookies_to_session(page)
        api_url = "https://outlook.office.com/api/v2.0/me/messages?$top=20&$select=Subject,From,Id,ReceivedDateTime"
        try:
            resp = s.get(api_url, timeout=15)
            data = resp.json()
            emails = []
            for item in data.get('value', []):
                sender = item.get('From', {}).get('EmailAddress', {}).get('Address', 'Unknown')
                name = item.get('From', {}).get('EmailAddress', {}).get('Name', sender)
                emails.append({
                    'sender': f"{name} <{sender}>",
                    'subject': item.get('Subject', 'No Subject'),
                    'msg_id': item.get('Id', ''),
                    'provider': PROVIDER_OUTLOOK,
                    'time': item.get('ReceivedDateTime', ''),
                })
            return emails
        except Exception:
            return []

    def read_email(self, page, msg_id):
        s = self._cookies_to_session(page)
        api_url = f"https://outlook.office.com/api/v2.0/me/messages/{msg_id}"
        try:
            resp = s.get(api_url, timeout=15)
            data = resp.json()
            body = data.get('Body', {}).get('Content', '')
            if body:
                import html as html_mod
                body = re.sub(r'<[^>]+>', '', body)
                body = html_mod.unescape(body).strip()
            return body or (data.get('BodyPreview', ''))
        except Exception:
            return ""

    def send_email(self, page, config, to, subject, body):
        s = self._cookies_to_session(page)
        api_url = "https://outlook.office.com/api/v2.0/me/sendmail"
        msg = {
            "Message": {
                "Subject": subject,
                "Body": {"ContentType": "Text", "Content": body},
                "ToRecipients": [{"EmailAddress": {"Address": to}}],
            },
            "SaveToSentItems": True,
        }
        try:
            s.post(api_url, json=msg, timeout=15)
        except Exception:
            raise


class EmailApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.config = self._load_config()
        self.menu = None
        self.state = STATE_MENU
        self.emails = []
        self.current_email = None
        self.current_email_body = ""
        self.input_buf = ""
        self.setup_step = 0
        self.setup_data = {}
        self.compose_data = {}
        self.compose_step = 0
        self._busy = False
        self._pending_ui = []
        self._browser = None
        self._context = None
        self._page = None
        self._provider = self._get_provider()
        self._accounts = self._load_accounts()
        self._current_account = 0
        self._folders = {"inbox": [], "sent": [], "trash": []}
        self._current_folder = "inbox"
        self._signature = self.config.get("signature", "")
        self._search_query = ""
        self._search_results = []

    def _get_provider(self):
        ptype = self.config.get('provider', PROVIDER_GMAIL)
        if ptype == PROVIDER_OUTLOOK:
            return OutlookProvider(self)
        return GmailProvider(self)

    def _load_config(self):
        if os.path.exists(EMAIL_CONFIG_PATH):
            try:
                with open(EMAIL_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    if 'password' in data:
                        try:
                            data['password'] = decrypt(data['password'])
                        except Exception:
                            pass
                    return data
            except Exception:
                return {}
        return {}

    def _load_accounts(self):
        return self.config.get("accounts", [{"provider": self.config.get("provider", PROVIDER_GMAIL), "email": self.config.get("email", ""), "password": self.config.get("password", "")}]) if self.config else []

    def _save_accounts(self):
        self.config["accounts"] = self._accounts
        self.config["email"] = self._accounts[self._current_account]["email"] if self._accounts else ""
        self.config["provider"] = self._accounts[self._current_account]["provider"] if self._accounts else PROVIDER_GMAIL
        self._save_config(self.config)

    def _save_config(self, config):
        to_save = config.copy()
        if 'password' in to_save:
            to_save['password'] = encrypt(to_save['password'])
        with open(EMAIL_CONFIG_PATH, 'w') as f:
            json.dump(to_save, f)
        self.config = config
        self._provider = self._get_provider()

    def on_focus(self):
        if not self.config or not self.config.get('email'):
            self._start_setup()
        else:
            self._show_main_menu()

    def _show_main_menu(self):
        self.state = STATE_MENU
        self._busy = False
        root = MenuNode("Email")
        root.add_child(MenuNode("Inbox", self._show_folder_view, "i"))
        root.add_child(MenuNode("Sent", lambda: self._show_folder("sent"), "s"))
        root.add_child(MenuNode("Trash", lambda: self._show_folder("trash"), "t"))
        root.add_child(MenuNode("Compose", self._start_compose, "c"))
        root.add_child(MenuNode("Account Setup", self._start_setup))
        if len(self._accounts) > 1:
            root.add_child(MenuNode("Switch Account", self._switch_account))
        if self._signature:
            root.add_child(MenuNode("Edit Signature", self._edit_signature))
        self.menu = MenuSystem(root, self.speak)
        pname = self._provider.get_name()
        email = self._accounts[self._current_account]["email"] if self._accounts else 'Not Setup'
        self.speak(f"{pname} Email. Inbox, Sent, Trash, Compose.")
        self.window.update_text(f"Email ({pname}): {email}")

    def _start_setup(self):
        self.state = STATE_SETUP
        self.setup_step = 0
        self.setup_data = {}
        self.input_buf = ""
        self.speak("Account Setup. Choose provider: Gmail or Outlook. Type g or o.")
        self.window.update_text("Setup - Provider (g/o):")

    def _ensure_browser(self):
        if self._page is None:
            if not HAS_PLAYWRIGHT:
                raise RuntimeError("Playwright is not installed.")
            p = sync_playwright().start()
            self._browser = p
            self._context = self._browser.chromium.launch_persistent_context(
                user_data_dir=os.path.join(TECH_SOFT, "playwright_data"),
                headless=True,
                no_viewport=True
            )
            self._page = self._context.new_page()
            if os.path.exists(COOKIES_PATH):
                try:
                    with open(COOKIES_PATH, 'r') as f:
                        cookies = json.load(f)
                    self._context.add_cookies(cookies)
                except Exception:
                    pass

    def _save_cookies(self):
        try:
            cookies = self._context.cookies()
            with open(COOKIES_PATH, 'w') as f:
                json.dump(cookies, f)
        except Exception:
            pass

    def _show_folder_view(self):
        self._current_folder = "inbox"
        self._fetch_inbox()

    def _show_folder(self, name):
        self._current_folder = name
        self.state = STATE_FOLDERS
        items = self._folders.get(name, [])
        if not items:
            self.speak(f"{name.title()} is empty.")
            root = MenuNode(name.title())
            root.add_child(MenuNode("Back", self._show_main_menu))
            self.menu = MenuSystem(root, self.speak)
            self.menu.announce_current()
            return
        root = MenuNode(name.title())
        for i, item in enumerate(items):
            sender = item.get('sender', 'Unknown')
            subject = item.get('subject', 'No Subject')
            root.add_child(MenuNode(f"{sender}: {subject}", lambda idx=i: self._read_folder_item(idx)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _read_folder_item(self, idx):
        items = self._folders.get(self._current_folder, [])
        if idx < 0 or idx >= len(items):
            return
        item = items[idx]
        self.speak(f"From: {item.get('sender', 'Unknown')}. Subject: {item.get('subject', 'No Subject')}. Body: {item.get('body', '')[:200]}")

    def _switch_account(self):
        self._current_account = (self._current_account + 1) % len(self._accounts)
        acct = self._accounts[self._current_account]
        self.config.update(acct)
        self._provider = self._get_provider()
        self.speak(f"Switched to {acct.get('email', 'Account')}.")
        self._show_main_menu()

    def _edit_signature(self):
        self.state = STATE_SETUP
        self.setup_step = 3
        self.input_buf = self._signature
        self.speak(f"Current signature: {self._signature}. Type new signature or press Enter to keep.")
        self.window.update_text(f"Signature: {self._signature}")

    def _fetch_inbox(self):
        if not HAS_PLAYWRIGHT:
            self._pending_ui.append(('error', "Playwright not installed."))
            return
        self._busy = True
        self.speak("Fetching emails...")
        self.window.update_text("Fetching...")
        threading.Thread(target=self._do_fetch_inbox, daemon=True).start()

    def _do_fetch_inbox(self):
        try:
            self._ensure_browser()
            page = self._provider.login(self._page, self.config)
            self._save_cookies()
            emails = self._provider.fetch_inbox(page, self.config)
            self._pending_ui.append(('inbox', emails))
        except Exception as e:
            self._pending_ui.append(('error', f"Failed to fetch inbox: {e}"))

    def _show_inbox_menu(self):
        self.state = STATE_INBOX
        if not self.emails:
            self.speak("Inbox empty.")
            return
        root = MenuNode("Inbox")
        for i, e in enumerate(self.emails):
            has_att = e.get('attachments', [])
            att_tag = " [attachments]" if has_att else ""
            root.add_child(MenuNode(f"{e['sender']}. {e['subject']}{att_tag}", lambda idx=i: self._read_email(idx)))
        if self._search_query:
            root.add_child(MenuNode(f"[Search: {self._search_query}]", lambda: self._search_inbox()))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _read_email(self, idx):
        self.state = STATE_READING
        self.current_email = self.emails[idx]
        self._current_email_idx = idx
        msg_id = self.current_email.get('msg_id', '')
        if msg_id:
            threading.Thread(target=self._do_read_email, args=(msg_id,), daemon=True).start()
        self.speak(f"From: {self.current_email['sender']}. Subject: {self.current_email['subject']}. Fetching content. F2 move to trash, F3 move to sent.")
        self.window.update_text(f"Reading: {self.current_email['subject']}")

    def _do_read_email(self, msg_id):
        try:
            body = self._provider.read_email(self._page, msg_id)
            self.current_email_body = body
            preview = body[:500] + "..." if len(body) > 500 else body
            self.speak(preview)
            self.window.update_text(body[:200])
        except Exception as e:
            self.speak(f"Error loading email: {e}")

    def _move_to_trash(self):
        if self.current_email and self._current_email_idx < len(self.emails):
            email = self.emails.pop(self._current_email_idx)
            self._folders.setdefault("trash", []).append(email)
            self.speak("Moved to trash.")
            if self.emails:
                self._show_inbox_menu()
            else:
                self._show_main_menu()

    def _move_to_sent(self):
        if self.current_email and self._current_email_idx < len(self.emails):
            email = self.emails.pop(self._current_email_idx)
            self._folders.setdefault("sent", []).append(email)
            self.speak("Moved to sent.")
            if self.emails:
                self._show_inbox_menu()
            else:
                self._show_main_menu()

    def _start_compose(self):
        self.state = STATE_COMPOSE
        self.compose_step = 0
        self.compose_data = {}
        self.input_buf = ""
        self.speak("Compose. Enter recipient email. F6 to toggle signature.")
        self.window.update_text("To:")

    def _search_inbox(self):
        self.state = STATE_SEARCH
        self.input_buf = self._search_query
        self.speak(f"Search inbox. Current query: {self._search_query or 'empty'}")
        self.window.update_text(f"Search: {self._search_query}")

    def _do_search_inbox(self):
        q = self.input_buf.strip().lower()
        if not q:
            self.speak("No search text.")
            return
        self._search_query = q
        self._search_results = [e for e in self.emails if q in e.get('subject', '').lower() or q in e.get('sender', '').lower()]
        if self._search_results:
            self._show_search_results()
        else:
            self.speak("No matches.")

    def _show_search_results(self):
        self.state = STATE_SEARCH
        root = MenuNode(f"Search: {self._search_query}")
        for i, e in enumerate(self._search_results):
            root.add_child(MenuNode(f"{e['sender']}. {e['subject']}", lambda idx=i: self._read_search_result(idx)))
        root.add_child(MenuNode("Back", self._show_inbox_menu))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _read_search_result(self, idx):
        if idx < 0 or idx >= len(self._search_results):
            return
        email = self._search_results[idx]
        self.current_email = email
        self._current_email_idx = self.emails.index(email) if email in self.emails else -1
        self.state = STATE_READING
        msg_id = email.get('msg_id', '')
        if msg_id:
            threading.Thread(target=self._do_read_email, args=(msg_id,), daemon=True).start()
        self.speak(f"From: {email['sender']}. Subject: {email['subject']}. Fetching content.")
        self.window.update_text(f"Reading: {email['subject']}")

    def _process_pending_ui(self):
        while self._pending_ui:
            action, data = self._pending_ui.pop(0)
            self._busy = False
            if action == 'inbox':
                self.emails = data
                self._show_inbox_menu()
            elif action == 'error':
                self.speak(data)
            elif action == 'sent':
                self.speak("Email sent successfully.")
                self._show_main_menu()
            elif action == 'send_error':
                self.speak("Failed to send. Check your connection.")

    def on_key(self, vk):
        self._process_pending_ui()

        if vk == win32con.VK_ESCAPE:
            if self.state == STATE_READING:
                self._show_inbox_menu()
            elif self.state == STATE_FOLDERS:
                self._show_main_menu()
            elif self.state == STATE_SEARCH:
                self._show_inbox_menu()
            elif self.state in (STATE_INBOX, STATE_SETUP, STATE_COMPOSE):
                self._show_main_menu()
            else:
                self.exit_app()
            return True

        if self._busy:
            return True

        if self.state == STATE_MENU:
            self._handle_menu(vk)
        elif self.state == STATE_INBOX:
            self._handle_inbox(vk)
        elif self.state == STATE_SETUP:
            self._handle_setup(vk)
        elif self.state == STATE_COMPOSE:
            self._handle_compose(vk)
        elif self.state == STATE_FOLDERS:
            self._handle_inbox(vk)
        elif self.state == STATE_SEARCH:
            self._handle_inbox(vk)
        elif self.state == STATE_READING:
            self._handle_reading(vk)

    def _handle_reading(self, vk):
        if vk == win32con.VK_F2:
            self._move_to_trash()
        elif vk == win32con.VK_F3:
            self._move_to_sent()
        elif vk == win32con.VK_BACK or vk == win32con.VK_ESCAPE:
            self._show_inbox_menu()

    def _handle_menu(self, vk):
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        if self.menu:
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Email: " + item.title)

    def _handle_inbox(self, vk):
        if vk == win32con.VK_F5:
            self._search_inbox()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Inbox: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self._busy:
                return
            if self.state in (STATE_MENU, STATE_INBOX, STATE_FOLDERS, STATE_SEARCH):
                if self.menu:
                    self.menu.next()
                    item = self.menu.get_current_item()
                    if item:
                        label = "Email: " if self.state == STATE_MENU else "Inbox: "
                        self.window.update_text(label + item.title)

    def _handle_setup(self, vk):
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if self.setup_step == 3:
                self._signature = self.input_buf
                self.config["signature"] = self._signature
                self._save_config(self.config)
                self.speak(f"Signature set: {self._signature}")
                self._show_main_menu()
                return
            if not val:
                return
            if self.setup_step == 0:
                val_lower = val.lower()
                if val_lower in ('g', 'gmail'):
                    self.setup_data['provider'] = PROVIDER_GMAIL
                elif val_lower in ('o', 'outlook'):
                    self.setup_data['provider'] = PROVIDER_OUTLOOK
                else:
                    self.speak("Type g for Gmail or o for Outlook.")
                    return
                self.setup_step = 1
                self.input_buf = ""
                pname = "Gmail" if self.setup_data['provider'] == PROVIDER_GMAIL else "Outlook"
                self.speak(f"{pname}. Enter email address.")
                self.window.update_text("Setup - Email:")
            elif self.setup_step == 1:
                self.setup_data['email'] = val
                self.setup_step = 2
                self.input_buf = ""
                self.speak("Enter app password or your account password.")
                self.window.update_text("Setup - Password:")
            elif self.setup_step == 2:
                self.setup_data['password'] = val
                self._accounts = [self.setup_data]
                self._current_account = 0
                self._save_config(self.setup_data)
                self.speak("Account saved.")
                self._show_main_menu()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf or " ")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(self.input_buf)
            if not (self.setup_step == 2):
                self.speak(ch)

    def _handle_compose(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._show_main_menu()
            return

        if vk == win32con.VK_F6:
            self._signature = self.input_buf if self.compose_step == 2 else self._signature
            self.speak(f"Signature toggled {'on' if not self._signature else 'off'}." if False else f"Signature: {'set' if self._signature else 'none'}")
            return

        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if self.compose_step < 2 and not val:
                return
            if self.compose_step == 0:
                self.compose_data['to'] = val
                self.compose_step = 1
                self.input_buf = ""
                self.speak("Subject.")
                self.window.update_text("Compose - Subject:")
            elif self.compose_step == 1:
                self.compose_data['subject'] = val
                self.compose_step = 2
                self.input_buf = ""
                self.speak(f"Type message body. Enter to send. Signature: {'on' if self._signature else 'off'}. F6 toggle.")
                self.window.update_text("Compose - Body:")
            elif self.compose_step == 2:
                self.compose_data['body'] = val
                if self._signature:
                    self.compose_data['body'] += "\n\n" + self._signature
                self._send_email()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf or " ")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(self.input_buf)
            self.speak(ch)

    def _send_email(self):
        if not HAS_PLAYWRIGHT:
            self._pending_ui.append(('send_error', None))
            return
        self._busy = True
        self.speak("Sending...")
        self.window.update_text("Sending...")
        threading.Thread(target=self._do_send_email, daemon=True).start()

    def _do_send_email(self):
        try:
            self._ensure_browser()
            page = self._provider.login(self._page, self.config)
            self._provider.send_email(page, self.config, self.compose_data['to'], self.compose_data['subject'], self.compose_data['body'])
            self._pending_ui.append(('sent', None))
        except Exception:
            self._pending_ui.append(('send_error', None))

    def close(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
            self._context = None
            self._page = None
