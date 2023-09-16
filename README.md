# loansim
Determine the optimal loan repayment strategy. You would think that immediately
paying down the loans is optimal, however my employer has a student loan repayment
match (limited to a certain amount each year). I wrote this script to calculate
how much I should pay off now, and how much I should drag out to capture future
student loan repayment matches.

## How to run
The script will attempt different increments of $1000 early payments, then
simulate what the next 10 years of repayment look like. It will report what
amount is optimal to pay now. Future paymens are adjusted by the `savings_rate`
to account for inflation, and the optimal strategy is described in adjuted
dollars.

```bash
python main.py --filename=loans.csv --savings_rate=0.04 --employer_amount=2500 --employer_month=11 --auto_pay_interest_discount=0.0025 -v=1
```

Optionally, you can include individual month's loan balances with`-v=3`,
although you might want to redirect to a file in that case:

```bash
python main.py --filename=loans.csv --savings_rate=0.04 --employer_amount=2500 --employer_month=11 --auto_pay_interest_discount=0.0025 -v=3 > output.txt
```