"""ATM Simulation - models real-life ATM problems.

Real-life scenarios handled:
  * PIN verification with card lockout after 3 wrong attempts
  * Insufficient balance and invalid amounts
  * Daily withdrawal limit
  * ATM cash running low / denomination-based dispensing
  * Deposits, balance enquiry, mini statement, PIN change
  * Money transfer between accounts
  * Data persisted to a JSON file
"""
import hashlib
import json
import os
from datetime import datetime, date

DATA_FILE = "accounts.json"
MAX_PIN_ATTEMPTS = 3
DAILY_WITHDRAW_LIMIT = 20000
DENOMINATIONS = [2000, 500, 200, 100]


class ATMError(Exception):
    """Base class for all ATM errors."""


class CardBlocked(ATMError):
    pass


class InvalidPin(ATMError):
    pass


class InsufficientFunds(ATMError):
    pass


class LimitExceeded(ATMError):
    pass


class ATMOutOfCash(ATMError):
    pass


class InvalidAmount(ATMError):
    pass


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


class Account:
    def __init__(self, card_no, name, pin_hash, balance=0.0, blocked=False,
                 failed_attempts=0, history=None, withdrawn_today=0.0,
                 last_withdraw_date=None):
        self.card_no = card_no
        self.name = name
        self.pin_hash = pin_hash
        self.balance = balance
        self.blocked = blocked
        self.failed_attempts = failed_attempts
        self.history = history or []
        self.withdrawn_today = withdrawn_today
        self.last_withdraw_date = last_withdraw_date

    def log(self, kind, amount):
        self.history.append({
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": kind,
            "amount": amount,
            "balance": self.balance,
        })

    def to_dict(self):
        return self.__dict__.copy()


class ATM:
    def __init__(self, data_file=DATA_FILE, cash=100000):
        self.data_file = data_file
        self.cash = {2000: 10, 500: 40, 200: 50, 100: 100}  # notes in machine
        self.accounts = {}
        self.current = None
        self._load()

    # ---------- persistence ----------
    def _load(self):
        if os.path.exists(self.data_file):
            with open(self.data_file) as f:
                for card, d in json.load(f).items():
                    self.accounts[card] = Account(**d)
        else:
            self.accounts = {
                "1001": Account("1001", "Amit", hash_pin("1234"), 50000),
                "1002": Account("1002", "Priya", hash_pin("4321"), 12000),
            }
            self._save()

    def _save(self):
        with open(self.data_file, "w") as f:
            json.dump({k: v.to_dict() for k, v in self.accounts.items()}, f, indent=2)

    # ---------- helpers ----------
    def _need_login(self):
        if not self.current:
            raise ATMError("Please insert card and login first.")

    @staticmethod
    def _check_amount(amount):
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise InvalidAmount("Amount must be a positive number.")

    def cash_available(self):
        return sum(d * n for d, n in self.cash.items())

    def _plan_dispense(self, amount):
        """Greedy note plan using notes available in the machine."""
        plan, remaining = {}, int(amount)
        for d in DENOMINATIONS:
            use = min(remaining // d, self.cash[d])
            if use:
                plan[d] = use
                remaining -= d * use
        if remaining:
            raise ATMOutOfCash("ATM cannot dispense this amount with available notes.")
        return plan

    # ---------- operations ----------
    def login(self, card_no, pin):
        acc = self.accounts.get(card_no)
        if not acc:
            raise ATMError("Card not recognised.")
        if acc.blocked:
            raise CardBlocked("Card is blocked. Contact your bank.")
        if acc.pin_hash != hash_pin(pin):
            acc.failed_attempts += 1
            if acc.failed_attempts >= MAX_PIN_ATTEMPTS:
                acc.blocked = True
                self._save()
                raise CardBlocked("Too many wrong PINs. Card blocked.")
            left = MAX_PIN_ATTEMPTS - acc.failed_attempts
            self._save()
            raise InvalidPin(f"Wrong PIN. {left} attempt(s) left.")
        acc.failed_attempts = 0
        self.current = acc
        self._save()
        return acc.name

    def logout(self):
        self.current = None

    def balance(self):
        self._need_login()
        return self.current.balance

    def deposit(self, amount):
        self._need_login()
        self._check_amount(amount)
        self.current.balance += amount
        self.current.log("DEPOSIT", amount)
        self._save()
        return self.current.balance

    def withdraw(self, amount):
        self._need_login()
        self._check_amount(amount)
        acc = self.current
        if amount % 100:
            raise InvalidAmount("Amount must be a multiple of 100.")
        today = str(date.today())
        if acc.last_withdraw_date != today:
            acc.withdrawn_today, acc.last_withdraw_date = 0.0, today
        if acc.withdrawn_today + amount > DAILY_WITHDRAW_LIMIT:
            raise LimitExceeded(
                f"Daily limit {DAILY_WITHDRAW_LIMIT} exceeded. "
                f"Remaining today: {DAILY_WITHDRAW_LIMIT - acc.withdrawn_today}")
        if amount > acc.balance:
            raise InsufficientFunds("Insufficient balance.")
        if amount > self.cash_available():
            raise ATMOutOfCash("ATM has insufficient cash.")
        plan = self._plan_dispense(amount)
        for d, n in plan.items():
            self.cash[d] -= n
        acc.balance -= amount
        acc.withdrawn_today += amount
        acc.log("WITHDRAW", amount)
        self._save()
        return plan

    def transfer(self, to_card, amount):
        self._need_login()
        self._check_amount(amount)
        target = self.accounts.get(to_card)
        if not target or target is self.current:
            raise ATMError("Invalid destination account.")
        if amount > self.current.balance:
            raise InsufficientFunds("Insufficient balance.")
        self.current.balance -= amount
        target.balance += amount
        self.current.log(f"TRANSFER OUT to {to_card}", amount)
        target.log(f"TRANSFER IN from {self.current.card_no}", amount)
        self._save()

    def change_pin(self, old, new):
        self._need_login()
        if self.current.pin_hash != hash_pin(old):
            raise InvalidPin("Old PIN is incorrect.")
        if not (new.isdigit() and len(new) == 4):
            raise InvalidPin("New PIN must be exactly 4 digits.")
        self.current.pin_hash = hash_pin(new)
        self._save()

    def mini_statement(self, n=5):
        self._need_login()
        return self.current.history[-n:]


# ---------- command line interface ----------
def main():
    atm = ATM()
    print("=== Welcome to Python ATM ===")
    card = input("Enter card number: ").strip()
    pin = input("Enter PIN: ").strip()
    try:
        print("Hello,", atm.login(card, pin))
    except ATMError as e:
        print("Error:", e)
        return

    menu = ("\n1.Balance 2.Deposit 3.Withdraw 4.Transfer "
            "5.Mini statement 6.Change PIN 7.Exit\n> ")
    while True:
        choice = input(menu).strip()
        try:
            if choice == "1":
                print("Balance:", atm.balance())
            elif choice == "2":
                print("New balance:", atm.deposit(float(input("Amount: "))))
            elif choice == "3":
                plan = atm.withdraw(int(input("Amount: ")))
                print("Collect cash:", ", ".join(f"{n} x {d}" for d, n in plan.items()))
            elif choice == "4":
                atm.transfer(input("To card no: ").strip(), float(input("Amount: ")))
                print("Transfer successful.")
            elif choice == "5":
                for t in atm.mini_statement():
                    print(t["time"], t["type"], t["amount"], "bal:", t["balance"])
            elif choice == "6":
                atm.change_pin(input("Old PIN: "), input("New PIN: "))
                print("PIN changed.")
            elif choice == "7":
                atm.logout()
                print("Thank you. Take your card.")
                break
            else:
                print("Invalid choice.")
        except ValueError:
            print("Error: please enter a valid number.")
        except ATMError as e:
            print("Error:", e)


if __name__ == "__main__":
    main()
