import argparse
import csv
from dataclasses import dataclass
import math

parser = argparse.ArgumentParser(
    prog='LoanSim', description='Simulate certain loan repayment strategies.')
parser.add_argument(
    '--filename',
    type=str,
    help='The name of the loan file, which should be a csv with these columns: '
    '[name, principal, current_interest, interest_rate]')

parser.add_argument(
    '--savings_rate',
    type=float,
    help=
    'Interest rate of savings account. Used to compare keeping the money in a savings account, but could be used for estimated market return, or other investments.'
)

parser.add_argument('--employeer_amount',
                    type=float,
                    help='Amount employeer would contribute each year.',
                    default=None)

parser.add_argument(
    '--employeer_month',
    type=int,
    help=
    'Month of the year to expect employeer contribution. Jan is 0, Dec is 11.',
    default=None)

parser.add_argument('-v',
                    '--verbose',
                    type=bool,
                    help='Whether to print verbose simulation details.',
                    default=None)

EXPECTED_COLUMNS = ('name', 'principal', 'current_interest', 'interest_rate')


@dataclass
class Loan:
    name: str
    principle_pennies: int
    current_interest_pennies: int
    interest_rate: float

    @property
    def balance(self) -> int:
        return self.principle_pennies + self.current_interest_pennies

    @property
    def daily_rate(self) -> float:
        return self.interest_rate / 365.25

    @property
    def monthly_rate(self) -> float:
        # Daily rate compounded across a year,
        # then back out an equivalent monthly rate.
        return (((1 + self.daily_rate)**365)**(1 / 12) - 1)

    def accrue_one_month_interest(self):
        interest = math.ceil(self.balance * self.monthly_rate)
        self.current_interest_pennies += interest

    def minimum_payment_pennies(self, months_remaining: int) -> int:
        numerator = self.monthly_rate * (
            (1 + self.monthly_rate)**months_remaining)
        denominator = ((1 + self.monthly_rate)**months_remaining) - 1
        return math.ceil(self.balance * (numerator / denominator))

    def make_payment(self, amount_pennies: int):
        if amount_pennies < self.current_interest_pennies:
            self.current_interest_pennies -= amount_pennies
            return
        amount_pennies -= self.current_interest_pennies
        self.current_interest_pennies = 0
        self.principle_pennies -= amount_pennies
        assert self.principle_pennies >= 0, f'Overpaid loan {self.name} by {-self.balance/100}'


class LoanPortfolio:

    def __init__(self, loans: list[Loan]):
        self.loans = list(loans)
        # Put loans in decreasing interest rate.
        self.loans.sort(key=lambda l: l.interest_rate, reverse=True)

    def balance_pennies(self) -> int:
        return sum(l.balance for l in self.loans)

    def minimum_payment(self, months_remaining: int) -> int:
        return sum(
            l.minimum_payment_pennies(months_remaining) for l in self.loans)

    def simulate_one_month_minimum_payments(self, months_remaining: int) -> int:
        amount_paid = 0
        # Accrue interest
        for l in self.loans:
            minimum = l.minimum_payment_pennies(months_remaining)
            l.accrue_one_month_interest()
            # Make minimum payments
            amount_paid += minimum
            l.make_payment(minimum)
        return amount_paid

    def make_additional_payment(self, amount: int):
        for l in self.loans:
            # Finished spending the amount.
            if amount <= 0:
                break
            # Loan is paid off.
            if l.balance <= 0:
                continue
            # We can pay off the whole loan and maybe then some.
            if l.balance <= amount:
                amount -= l.balance
                l.make_payment(l.balance)
                continue
            l.make_payment(amount)
            return


def load_loans(filename: str) -> list[Loan]:
    res = []
    with open(filename, mode='rt', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        assert tuple(
            header
        ) == EXPECTED_COLUMNS, f'Columns expected to be {EXPECTED_COLUMNS}'
        for i, row in enumerate(reader):
            loan = Loan(name=row[0],
                        principle_pennies=math.ceil(float(row[1]) * 100),
                        current_interest_pennies=math.ceil(float(row[2]) * 100),
                        interest_rate=float(row[3]))
            assert loan.principle_pennies >= 0, f'[row {i}] {loan.name} principal should be positive.'
            assert loan.current_interest_pennies >= 0, f'[row {i}] {loan.name} current_interest should be positive.'
            assert 1.0 > loan.interest_rate >= 0, f'[row {i}] {loan.name} interest_rate should be between 0.0 and 1.0.'
            res.append(loan)

    return res


@dataclass
class PaymentHistory:
    savings_rate: float
    real_pennies: int = 0.0
    adjusted_pennies: float = 0.0

    def make_payment(self, amount: int, months_in_the_future: int):
        self.real_pennies += amount
        self.adjusted_pennies += amount / (
            (1 + (self.savings_rate / 12))**months_in_the_future)


class Simulation:

    def __init__(self):
        args = parser.parse_args()
        self.verbose = args.verbose
        self.portfolio = LoanPortfolio(load_loans(args.filename))
        self.payments_history = PaymentHistory(args.savings_rate)

        assert ((args.employeer_amount is None and args.employeer_month is None)
                or (args.employeer_amount is not None and
                    args.employeer_month is not None))
        self.employeer_amount = args.employeer_amount*100
        self.employeer_month = args.employeer_month

    def print_monthly_stats(self, months_remaining: int):
        print(
            f'[{months_remaining}] Loans: {self.portfolio.balance_pennies()/100} Total Paid: {self.payments_history.real_pennies/100}'
        )
        if not self.verbose:
            return
        for l in self.portfolio.loans:
            print(f'\t{l.name} {l.interest_rate} {l.balance/100}')

    def make_early_payment(self, amount_pennies:int):
        self.portfolio.make_additional_payment(amount_pennies)
        self.payments_history.make_payment(amount_pennies, 0)

    def simulate_all(self):
        #Hardcoded for now.
        months_remaining = 120
        current_month = 9

        while months_remaining > 0:
            #self.print_monthly_stats(months_remaining)
            minimum_payment = self.portfolio.simulate_one_month_minimum_payments(
                months_remaining)

            bill = minimum_payment

            if current_month == self.employeer_month:
                bill -= self.employeer_amount

            if bill > 0:
                self.payments_history.make_payment(bill, (120-months_remaining)+1)
            elif bill < 0:
                self.portfolio.make_additional_payment(-bill)

            months_remaining -= 1
            current_month = (current_month + 1) % 12
        #self.print_monthly_stats(months_remaining)



def main():

    best_total = None
    best_early_payment = None
    baseline_sim = Simulation()
    for early_payment in range(int(baseline_sim.portfolio.balance_pennies()/(1000*100))):
        early_payment = 1000*early_payment
        sim = Simulation()
        sim.make_early_payment(early_payment*100)
        sim.simulate_all()
        print(f'{early_payment}: {sim.payments_history}')
        if best_total is None or sim.payments_history.adjusted_pennies < best_total:
            best_total = sim.payments_history.adjusted_pennies
            best_early_payment = early_payment
    print(f'Best early payment: {best_early_payment} results in {best_total/100}')



if __name__ == '__main__':
    main()