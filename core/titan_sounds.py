import os
from core.audio_player import AudioPlayer


class TitanSounds:
    def __init__(self):
        self.audio = AudioPlayer()
        self.theme = 'windows 9x theme'
        self._find_sfx_dirs()

    def _find_sfx_dirs(self):
        self._search_dirs = []
        appdata = os.getenv('APPDATA')
        if appdata:
            user_sfx = os.path.join(appdata, 'titosoft', 'Titan', 'sfx')
            self._search_dirs.append(user_sfx)
        titan_sfx = r'C:\titan\titan_data\sfx'
        self._search_dirs.append(titan_sfx)
        titan_root_sfx = r'C:\titan\sfx'
        self._search_dirs.append(titan_root_sfx)
        for d in self._search_dirs:
            if not os.path.isdir(d):
                self._search_dirs.remove(d)

    def _resolve(self, *parts):
        for base in self._search_dirs:
            path = os.path.join(base, self.theme, *parts)
            if os.path.exists(path):
                return path
            path = os.path.join(base, 'default', *parts)
            if os.path.exists(path):
                return path
            path = os.path.join(base, *parts)
            if os.path.exists(path):
                return path
        return None

    def _play(self, *parts):
        path = self._resolve(*parts)
        if path:
            self.audio.play_file(path)

    def play_focus(self):
        self._play('core', 'FOCUS.ogg')

    def play_select(self):
        self._play('core', 'SELECT.ogg')

    def play_dialog(self):
        self._play('ui', 'dialog.ogg')

    def play_dialog_close(self):
        self._play('ui', 'dialogclose.ogg')

    def play_endoflist(self):
        self._play('ui', 'endoflist.ogg')

    def play_error(self):
        self._play('core', 'error.ogg')

    def play_applist(self):
        self._play('ui', 'applist.ogg')

    def play_statusbar(self):
        self._play('ui', 'statusbar.ogg')

    def play_startup(self):
        self._play('core', 'startup.ogg')

    def play_new_message(self):
        self._play('titannet', 'new_message.ogg')

    def play_message_send(self):
        self._play('titannet', 'message_send.ogg')

    def play_chat_message(self):
        self._play('titannet', 'chat_message.ogg')

    def play_online(self):
        self._play('titannet', 'online.ogg')

    def play_offline(self):
        self._play('titannet', 'offline.ogg')

    def play_welcome(self):
        self._play('titannet', 'welcome to IM.ogg')

    def play_account_created(self):
        self._play('titannet', 'account_created.ogg')
