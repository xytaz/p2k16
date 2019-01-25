
from datetime import datetime


import pandas
from matplotlib import pyplot as plt


"""
\COPY (SELECT id,email FROM account) TO '/tmp/accounts.csv' CSV HEADER;
\COPY (SELECT created_by AS account_id,start_date,end_date,amount FROM stripe_payment) TO '/tmp/payments.csv' CSV HEADER;
"""


def report(periods):
    print(periods.head(3))

    print(periods.periods.median())

    short_threshold = 3
    short = periods[periods.periods < short_threshold]

    onemonth = periods[periods.periods == 1]

    print(len(periods))
    print(len(short))
    print(len(onemonth))

def find_payments(payments):
    #assert payments.account_id.unique() == 1
    bydate = payments.sort_values('start_date', ascending=True).start_date
    first = bydate.iloc[0]
    last = bydate.iloc[-1]
    assert last >= first, (last, first)
    s = pandas.Series({'first': first, 'last': last})
    return s

# TODO: calculate percentage churn
# TODO: cauculate cohort falloff
def report_monthly(accounts, payments, start='2005-1-1', end='2018-12-1'):

    monthly = pandas.DataFrame()

    firstlast = payments.groupby('account_id').apply(find_payments)
    firstlast['first'] = firstlast['first'].astype('datetime64[ns]')
    firstlast['last'] = firstlast['last'].astype('datetime64[ns]')    
    started_monthly = firstlast.groupby(pandas.Grouper(freq='M', key='first'))
    stopped_monthly = firstlast.groupby(pandas.Grouper(freq='M', key='last'))

    payments_dated = payments.copy()
    payments_dated.index = payments.start_date
    payments_monthly = payments_dated.groupby(pandas.Grouper(freq='M'))

    monthly['paying'] = payments_monthly.count().account_id
    monthly['stopped'] = stopped_monthly.count()
    monthly['started'] = started_monthly.count()
    monthly['growth'] = monthly.started - monthly.stopped

    # Crop to relevant timeperiod
    monthly = monthly[start:end]

    print('monthly', monthly.paying.head())

    # Plotting
    fig, (total_ax, growth_ax, start_ax, stop_ax) = plt.subplots(4, figsize=(16,16))
    fig.suptitle('Bitraf membership statistics (monthly)')

    monthly.plot(ax=total_ax, y='paying',
                title='Total paying members')

    monthly.plot(ax=start_ax,
                y=['started'],
                title='Persons stopping membership',
                legend=False)
    monthly.plot(ax=stop_ax,
                y=['stopped'],
                title='Persons stopping membership',
                legend=False)

    monthly.plot(color='black', ax=growth_ax, y='growth',
                title='Net growth in membership',
                style='_', legend=False)
    growth_ax.axhspan(0, growth_ax.get_ylim()[1], color='green', alpha=0.5)
    growth_ax.axhspan(0, growth_ax.get_ylim()[0], color='red', alpha=0.5)

    fig.savefig('monthly.png')
    monthly.to_csv('monthly.csv')    
    print('wrote monthly report')

    return monthly


def report_misc(accounts, payments):

    member_periods = payments.groupby('account_id')
    print('Lifetime paying members', len(member_periods))

    print('Average membership price: {} kr'.format(int(payments.amount.mean())))

    end = datetime.utcnow()
    paying = payments[ payments.end_date >= end]
#    print('p', paying.head())
    print('Currently paying members', len(paying))


def main():
    accounts = pandas.read_csv('accounts.csv')
    payments = pandas.read_csv('payments.csv', parse_dates=['end_date', 'start_date'])

    report_misc(accounts, payments)
    report_monthly(accounts, payments)

    #df = pandas.read_csv('memberstats.csv')
    #report(df)

if __name__ == '__main__':
    main()
