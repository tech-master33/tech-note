import os
import json
import datetime
import csv
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

DATA_FILE = os.path.join(TECH_SOFT, "expenses.json")

CATEGORIES = ["Food", "Transport", "Housing", "Utilities", "Entertainment", "Health", "Shopping", "Other"]


class ExpenseTracker(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.expenses = self._load_data()
        self._input_mode = None
        self._input_text = ""
        self._new_expense = {}
        self._build_menu()

    def _load_data(self):
        try:
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def _save_data(self):
        try:
            os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
            with open(DATA_FILE, 'w') as f:
                json.dump(self.expenses, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("Expense Tracker")
        root.add_child(MenuNode("Add Expense", self._start_add))
        root.add_child(MenuNode("View All", self._view_all))
        root.add_child(MenuNode("By Category", self._view_categories))
        root.add_child(MenuNode("Monthly Total", self._monthly_total))
        root.add_child(MenuNode("Export CSV", self._export_csv))
        total = sum(e.get("amount", 0) for e in self.expenses)
        root.add_child(MenuNode(f"Total: ${total:.2f}"))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _start_add(self):
        self._input_mode = "amount"
        self._input_text = ""
        self._new_expense = {"date": datetime.date.today().isoformat()}
        self.speak("Enter amount.")
        self.window.update_text("Amount: $")

    def _finish_add(self):
        self._new_expense.setdefault("category", "Other")
        self._new_expense.setdefault("description", "")
        self.expenses.append(self._new_expense)
        self._save_data()
        self.speak(f"Expense added: ${self._new_expense.get('amount', 0):.2f}.")
        self._input_mode = None
        self._build_menu()
        self.menu.announce_current()

    def _view_all(self):
        if not self.expenses:
            self.speak("No expenses.")
            return
        root = MenuNode("All Expenses")
        for e in reversed(self.expenses[-50:]):
            label = f"${e['amount']:.2f} {e.get('category','')} {e.get('date','')}"
            if e.get("description"):
                label += f" - {e['description'][:30]}"
            root.add_child(MenuNode(label))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _view_categories(self):
        root = MenuNode("By Category")
        for cat in CATEGORIES:
            total = sum(e.get("amount", 0) for e in self.expenses if e.get("category") == cat)
            count = sum(1 for e in self.expenses if e.get("category") == cat)
            if count > 0:
                root.add_child(MenuNode(f"{cat}: ${total:.2f} ({count} items)", lambda c=cat: self._show_category(c)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        if not root.children:
            root.add_child(MenuNode("No expenses"))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _show_category(self, cat):
        items = [e for e in self.expenses if e.get("category") == cat]
        root = MenuNode(cat)
        for e in reversed(items[-30:]):
            root.add_child(MenuNode(f"${e['amount']:.2f} {e.get('date','')}"))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _monthly_total(self):
        if not self.expenses:
            self.speak("No expenses.")
            return
        by_month = {}
        for e in self.expenses:
            m = e.get("date", "")[:7]
            by_month[m] = by_month.get(m, 0) + e.get("amount", 0)
        lines = [f"{m}: ${v:.2f}" for m, v in sorted(by_month.items(), reverse=True)[:12]]
        self.speak(". ".join(lines))
        self.window.update_text(" | ".join(lines))

    def _export_csv(self):
        path = os.path.join(TECH_SOFT, "expenses_export.csv")
        try:
            with open(path, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(["Date", "Amount", "Category", "Description"])
                for e in self.expenses:
                    w.writerow([e.get("date", ""), e.get("amount", 0), e.get("category", ""), e.get("description", "")])
            self.speak(f"Exported {len(self.expenses)} expenses to expenses_export.csv.")
        except:
            self.speak("Export failed.")

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Expense Tracker. " + (item.title if item else ""))

    def on_key(self, vk):
        if self._input_mode:
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "amount":
                    try:
                        self._new_expense["amount"] = float(self._input_text)
                        self._input_mode = "category"
                        self._input_text = ""
                        self.speak("Select category. Press Enter for Other.")
                        self.window.update_text("Category (Enter=Other): ")
                    except:
                        self.speak("Invalid amount.")
                elif self._input_mode == "category":
                    self._new_expense["category"] = self._input_text.strip() or "Other"
                    self._input_mode = "description"
                    self._input_text = ""
                    self.speak("Enter description, or press Enter to skip.")
                    self.window.update_text("Description: ")
                elif self._input_mode == "description":
                    self._new_expense["description"] = self._input_text.strip()
                    self._finish_add()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(f"{self._input_mode}: {self._input_text}")
            return
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if self._input_mode:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if self._input_mode:
            return "Type value. Enter to confirm, Escape to cancel."
        return "Expense Tracker. Track spending by category. Export to CSV. Space next, Backspace previous. Escape exit."
