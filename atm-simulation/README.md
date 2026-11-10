# Python ATM Simulation

A command-line ATM simulator that models real-life banking problems.

## Real-life problems handled
- PIN verification, card **blocked after 3 wrong attempts**
- **Insufficient balance** and invalid amount checks (negative, not a multiple of 100)
- **Daily withdrawal limit** (Rs. 20,000)
- **ATM runs out of cash** / cannot form the amount from available notes
- Cash dispensed in **denominations** (2000, 500, 200, 100)
- Deposit, balance enquiry, mini statement, PIN change, money transfer
- PINs stored as SHA-256 hashes; data persisted in `accounts.json`

## Run
```
python atm.py
```
Demo cards: `1001` / PIN `1234`, `1002` / PIN `4321`

## Test
```
python -m unittest test_atm.py -v
```

## Requirements
Python 3.8+ (standard library only).
