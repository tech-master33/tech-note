import os
import json
import win32con
import win32api
import imaplib
import smtplib
import email
import threading
from email.mime.text import MIMEText
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT
from core.crypto_util import encrypt, decrypt

EMAIL_CONFIG_PATH = os.path.join(TECH_SOFT, 'email_config.json')

STATE_MENU = 0
STATE_SETUP = 1
STATE_INBOX = 2
STATE_READING = 3
STATE_COMPOSE = 4

class EmailApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.config = self._load_config()
        self.menu = None
        self.state = STATE_MENU
        self.emails = []
        self.current_email_body = ""
        self.input_buf = ""
        self.setup_step = 0
        self.setup_data = {}
        self.compose_data = {}
        self.compose_step = 0
        self._busy = False

    def _load_config(self):
        if os.path.exists(EMAIL_CONFIG_PATH):
            try:
                with open(EMAIL_CONFIG_PATH, 'r') as f:
                    data = json.load(f)
                    if 'password' in data:
                        try:
                            data['password'] = decrypt(data['password'])
                        except:
                            pass
                    return data
            except:
                return {}
        return {}

    def _save_config(self, config):
        to_save = config.copy()
        if 'password' in to_save:
            to_save['password'] = encrypt(to_save['password'])
        with open(EMAIL_CONFIG_PATH, 'w') as f:
            json.dump(to_save, f)
        self.config = config

    def on_focus(self):
        if not self.config:
            self._start_setup()
        else:
            self._show_main_menu()

    def _show_main_menu(self):
        self.state = STATE_MENU
        self._busy = False
        root = MenuNode("Email")
        root.add_child(MenuNode("Inbox", self._fetch_inbox, "i"))
        root.add_child(MenuNode("Compose", self._start_compose, "c"))
        root.add_child(MenuNode("Account Setup", self._start_setup, "s"))
        self.menu = MenuSystem(root, self.speak)
        self.speak("Email Menu. Inbox, Compose, or Setup.")
        self.window.update_text("Email: " + self.config.get('email', 'Not Setup'))

    def _start_setup(self):
        self.state = STATE_SETUP
        self.setup_step = 0
        self.setup_data = {}
        self.input_buf = ""
        self.speak("Account Setup. Enter email address.")
        self.window.update_text("Setup - Email:")

    def _fetch_inbox(self):
        self._busy = True
        self.speak("Fetching emails...")
        self.window.update_text("Fetching...")
        threading.Thread(target=self._do_fetch_inbox, daemon=True).start()

    def _do_fetch_inbox(self):
        try:
            mail = imaplib.IMAP4_SSL(self.config.get('imap_server', 'imap.gmail.com'))
            mail.login(self.config['email'], self.config['password'])
            mail.select("inbox")
            status, messages = mail.search(None, 'ALL')
            
            ids = messages[0].split()
            recent_ids = ids[-10:]
            recent_ids.reverse()
            
            self.emails = []
            for i in recent_ids:
                res, msg_data = mail.fetch(i, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = msg['subject']
                        sender = msg['from']
                        
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                            
                        self.emails.append({
                            'subject': subject,
                            'sender': sender,
                            'body': body
                        })
            
            mail.close()
            mail.logout()
            
            if not self.emails:
                self.speak("Inbox empty.")
            else:
                self._show_inbox_menu()
        except Exception:
            self.speak("Connection failed. Check your email settings.")
        finally:
            self._busy = False

    def _show_inbox_menu(self):
        self.state = STATE_INBOX
        root = MenuNode("Inbox")
        for i, e in enumerate(self.emails):
            label = f"{e['sender'].split('<')[0]}. {e['subject']}"
            root.add_child(MenuNode(label, lambda idx=i: self._read_email(idx)))
        
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _read_email(self, idx):
        self.state = STATE_READING
        e = self.emails[idx]
        self.current_email_body = e['body']
        info = f"From: {e['sender']}. Subject: {e['subject']}. Content follows."
        self.speak(info)
        self.speak(self.current_email_body[:500] + "...")
        self.window.update_text(f"Reading: {e['subject']}")

    def _start_compose(self):
        self.state = STATE_COMPOSE
        self.compose_step = 0
        self.compose_data = {}
        self.input_buf = ""
        self.speak("Compose. Enter recipient email.")
        self.window.update_text("To:")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.state == STATE_READING:
                self._show_inbox_menu()
            elif self.state in (STATE_INBOX, STATE_SETUP, STATE_COMPOSE):
                self._show_main_menu()
            else:
                self.exit_app()
            return

        if self._busy:
            return

        if self.state == STATE_MENU:
            self._handle_menu(vk)
        elif self.state == STATE_INBOX:
            self._handle_inbox(vk)
        elif self.state == STATE_SETUP:
            self._handle_setup(vk)
        elif self.state == STATE_COMPOSE:
            self._handle_compose(vk)

    def _handle_menu(self, vk):
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        if self.menu:
            item = self.menu.get_current_item()
            if item: self.window.update_text("Email: " + item.title)

    def _handle_inbox(self, vk):
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        item = self.menu.get_current_item()
        if item: self.window.update_text("Inbox: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self._busy:
                return
            if self.state in (STATE_MENU, STATE_INBOX):
                if self.menu:
                    self.menu.next()
                    item = self.menu.get_current_item()
                    if item:
                        label = "Email: " if self.state == STATE_MENU else "Inbox: "
                        self.window.update_text(label + item.title)

    def _handle_setup(self, vk):
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val: return
            
            if self.setup_step == 0:
                self.setup_data['email'] = val
                domain = val.split('@')[-1].lower() if '@' in val else ""
                if 'gmail' in domain:
                    self.setup_data['imap_server'] = 'imap.gmail.com'
                    self.setup_data['smtp_server'] = 'smtp.gmail.com'
                elif 'outlook' in domain or 'hotmail' in domain:
                    self.setup_data['imap_server'] = 'imap-mail.outlook.com'
                    self.setup_data['smtp_server'] = 'smtp-mail.outlook.com'
                else:
                    self.setup_data['imap_server'] = 'imap.' + domain
                    self.setup_data['smtp_server'] = 'smtp.' + domain
                
                self.setup_step = 1
                self.input_buf = ""
                self.speak("Enter app password.")
                self.window.update_text("Setup - Password:")
            elif self.setup_step == 1:
                self.setup_data['password'] = val
                self._save_config(self.setup_data)
                self.speak("Account saved.")
                self._show_main_menu()
            return
            
        if self._handle_text_input(vk):
            pass

    def _handle_compose(self, vk):
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if self.compose_step < 2 and not val: return
            
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
                self.speak("Type message body. Enter to send.")
                self.window.update_text("Compose - Body:")
            elif self.compose_step == 2:
                self.compose_data['body'] = val
                self._send_email()
            return
            
        if self._handle_text_input(vk):
            pass

    def _send_email(self):
        self._busy = True
        self.speak("Sending...")
        self.window.update_text("Sending...")
        threading.Thread(target=self._do_send_email, daemon=True).start()

    def _do_send_email(self):
        try:
            server = smtplib.SMTP(self.config.get('smtp_server', 'smtp.gmail.com'), 587)
            server.starttls()
            server.login(self.config['email'], self.config['password'])
            
            msg = MIMEText(self.compose_data['body'])
            msg['Subject'] = self.compose_data['subject']
            msg['From'] = self.config['email']
            msg['To'] = self.compose_data['to']
            
            server.send_message(msg)
            server.quit()
            self.speak("Email sent successfully.")
            self._show_main_menu()
        except Exception:
            self.speak("Failed to send. Check your connection.")
            self.compose_step = 2
        finally:
            self._busy = False

    def _handle_text_input(self, vk):
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf if self.input_buf else " ")
            return True
        
        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            self.window.update_text(self.input_buf)
            if not (self.state == STATE_SETUP and self.setup_step == 1):
                self.speak(ch)
            return True
        return False
