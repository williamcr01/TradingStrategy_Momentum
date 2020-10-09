import backtrader as bt
import math
import matplotlib.pyplot as plt

port_val = []


class myStrategy(bt.Strategy):
    # Class with strategy to be backtested
    params = (
        ('oneplot', True),
        ('momosc', 12),
    )

    def __init__(self):

        self.buysize = None

        self.inds = dict()
        for i, d in enumerate(self.datas):
            self.inds[d] = dict()
            self.inds[d]['momosc'] = bt.indicators.MomentumOscillator(d.close, period=self.params.momosc)

            if i > 0:  # Check we are not on the first loop of data feed:
                if self.p.oneplot == True:
                    d.plotinfo.plotmaster = self.datas[0]

    def notify_order(self, order):
        # Function to notify if a trade has been executed or not
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                print('BUY EXECUTED, Size: {}, Price: {}, Cost: {}, Comm: {}'.format(
                    order.executed.size,
                    order.executed.price,
                    order.executed.value,
                    order.executed.comm))

                self.buysize = order.executed.size

            elif order.issell():
                print('SELL EXECUTED, Size {}, Price: {}, Total {}, Cost: {}, Comm {}'.format(
                    self.buysize,
                    order.executed.price,
                    self.buysize * order.executed.price,
                    order.executed.value,
                    order.executed.comm))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            print('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        if not trade.isclosed:
            return
        print('OPERATION PROFIT/LOSS, GROSS: {}, NET: {}'.format(
            trade.pnl,
            trade.pnlcomm))

    def next(self):
        # Function to handle buy and sell signals
        cash = self.broker.get_cash()
        # Loop through the different stocks and check for buy/sell signals
        for i, d in enumerate(self.datas):
            size_103 = math.floor((0.82 * cash) / d.close[0])
            size_101 = math.floor((0.5 * cash) / d.close[0])
            size_max = math.floor(cash / d.close[0])
            dt, dn = self.datetime.date(), d._name
            pos = self.getposition(d).size
            if not pos:
                if cash > d.close[0]:
                    if self.inds[d]['momosc'][0] > 103.5:
                        self.buy(data=d, size=size_max)
                        cash = 0
                        print('BUY CREATED: {} {} at {}'.format(size_max, dn, d.close[0]))
                    elif self.inds[d]['momosc'][0] >= 102.5:
                        self.buy(data=d, size=size_103)
                        cash -= (size_103 * d.close[0])
                        print('BUY CREATED: {} {} at {}'.format(size_103, dn, d.close[0]))
                    elif self.inds[d]['momosc'][0] > 100.5:
                        self.buy(data=d, size=size_101)
                        cash -= (size_101 * d.close[0])
                        print('BUY CREATED: {} {} {}'.format(size_101, dn, d.close[0]))
                else:
                    pass
            else:
                if self.inds[d]['momosc'][0] < 100:
                    self.sell(data=d, size=pos)
                    print('SELL CREATED: {} {} at {}'.format(pos, dn, d.close[0]))
                else:
                    pass
        value = self.broker.get_value()
        port_val.append(value)


class maxRiskSizer(bt.Sizer):
    # Function to calculate size of orders
    """
    Returns the number of shares rounded down that can be purchased for the
    max rish tolerance
    """
    params = (('risk', 0.03),)

    def __init__(self):
        if self.p.risk > 1 or self.p.risk < 0:
            raise ValueError('The risk parameter is a percentage which must be'
                             'entered as a float. e.g. 0.5')

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy == True:
            size = math.floor((cash * self.p.risk) / data[0])
        else:
            size = math.floor((cash * self.p.risk) / data[0]) * -1
        return size


def runstrat():
    # Function to run the strategy
    cerebro = bt.Cerebro()
    cerebro.broker = bt.brokers.BackBroker(slip_perc=0.0001, slip_open=True)  # Set slippage

    cerebro.addstrategy(myStrategy, oneplot=False)

    # create data list
    datalist = [
        ('path/to/.csv/file', 'NAME'),  # [0] = Data file, [1] = Data name
    ]

    # Loop through the list adding to cerebro.
    for i in range(len(datalist)):
        data = bt.feeds.YahooFinanceCSVData(dataname=datalist[i][0])
        cerebro.adddata(data, name=datalist[i][1])

    startcash = 100000
    cerebro.broker.setcash(startcash)
    # cerebro.addsizer(maxRiskSizer, risk=1)
    cerebro.broker.setcommission(commission=0.001)  # Set commission
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='mysharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='mydrawdown')
    run_strats = cerebro.run()
    run_strat = run_strats[0]

    # Get final portfolio Value
    portvalue = cerebro.broker.getvalue()
    pnl = portvalue - startcash

    # Print out the final result
    print('Final Portfolio Value: ${}'.format(portvalue))
    print('P/L: ${}'.format(pnl))
    print('Sharpe ratio: {}\n'
          'Max drawdown duration: {} days\n'
          'Max drawdown: {}%'.format
          (run_strat.analyzers.mysharpe.get_analysis()['sharperatio'],
           run_strat.analyzers.mydrawdown.get_analysis()['max']['len'],
           run_strat.analyzers.mydrawdown.get_analysis()['max']['drawdown'],
           ))

    # cerebro.plot(style='candlestick')

    fig, axes = plt.subplots(figsize=(12, 6))
    axes.plot(port_val)
    plt.show()


if __name__ == '__main__':
    runstrat()
