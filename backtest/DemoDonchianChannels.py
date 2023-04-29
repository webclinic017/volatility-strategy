import backtrader as bt
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (15,8)

cerebro = bt.Cerebro(stdstats=False)
cerebro.addobserver(bt.observers.BuySell)
cerebro.addobserver(bt.observers.Broker)

data = bt.feeds.GenericCSVData(
    dataname='dataMT5/EURUSDDaily2010.csv',
    nullvalue=0.0,
    timeframe=bt.TimeFrame.Days, 
    compression=1,
    fromdate=datetime(2020, 7, 8, 00, 00, 00),
    todate=datetime(2023, 3, 1, 00, 00, 00),
    dtformat=('%Y.%m.%d'),

    open=1,
    high=2,
    low=3,
    close=4,
    volume=5,
    openinterest=-1
)

cerebro.adddata(data)

class DonchianChannels(bt.Indicator):
    '''
    Params Note:
      - `lookback` (default: -1)
        If `-1`, the bars to consider will start 1 bar in the past and the
        current high/low may break through the channel.
        If `0`, the current prices will be considered for the Donchian
        Channel. This means that the price will **NEVER** break through the
        upper/lower channel bands.
    '''
    alias = ('DCH', 'DonchianChannel',)

    lines = ('dcm', 'dch', 'dcl',)  # dc middle, dc high, dc low
    params = dict(
        period_h=20,
        period_l=20,
        lookback=-1,  # consider current bar or not
    )

    plotinfo = dict(subplot=False)  # plot along with data
    plotlines = dict(
        dcm=dict(ls='--'),  # dashed line
        dch=dict(_samecolor=True),  # use same color as prev line (dcm)
        dcl=dict(_samecolor=True),  # use same color as prev line (dch)
    )
        
    def __init__(self):
        hi, lo = self.data.high, self.data.low
        if self.p.lookback:  # move backwards as needed
            hi, lo = hi(self.p.lookback), lo(self.p.lookback)

        self.l.dch = bt.ind.Highest(hi, period=self.p.period_h)
        self.l.dcl = bt.ind.Lowest(lo, period=self.p.period_l)
        self.l.dcm = (self.l.dch + self.l.dcl) / 2.0  # avg of the above

class DonchianChannelsStrategy(bt.Strategy):
    params = dict(
        period_h=20,
        period_l=10,
        stake=100,
    )

    def __init__(self):
        self.dcind = DonchianChannels(period_h=self.p.period_h, period_l=self.p.period_l)

    def next(self):
        if self.data[0] > self.dcind.dch[0]:
            self.buy(size=self.p.stake)
        elif self.data[0] < self.dcind.dcl[0]:
            self.sell(size=self.p.stake)

cerebro.broker.setcash(1000.0)
cerebro.broker.setcommission(commission=0.0, margin=0.02)
cerebro.broker.set_slippage_perc(perc=0.005)

cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn')

cerebro.addstrategy(DonchianChannelsStrategy, period_h=20, period_l=10)

result = cerebro.run()
strat = result[0]
print("--------------- AnnualReturn -----------------")
print(strat.analyzers._AnnualReturn.get_analysis())

AnReturn = strat.analyzers._AnnualReturn.get_analysis()
df = pd.DataFrame(AnReturn.values(), index=AnReturn.keys()).reset_index()
df.columns=['Year', 'AnnualReturn']
df.to_csv('DemoDonchianChannels.csv', index=False)

print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

figure = cerebro.plot(style='candlestick', volume=False,
                      barup = '#ff9896', bardown='#98df8a',
                      tickrotation=10, )[0][0]

figure.savefig('DemoDonchianChannels.png')