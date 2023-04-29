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

class DualMovingAverageStrategy(bt.Strategy):
    '''This strategy buys/sells upong the short moving average crossing
    upwards/downwards long moving average.
    '''
    params = dict(
        period_short=15,
        period_long=100,
        stake=1000,
    )

    def __init__(self):
        # To control operation entries
        self.orderid = None

        # Compute long and short moving averages
        smavg = bt.ind.SMA(period=self.p.period_short)
        lmavg = bt.ind.SMA(period=self.p.period_long)

        # Go long when short moving average is above long moving average
        self.signal = bt.ind.CrossOver(smavg, lmavg)

    def next(self):
        if self.signal > 0.0:  # cross upwards
            if self.position:
                self.close()
            self.orderid = self.buy(size=self.p.stake)

        elif self.signal < 0.0:
            if self.position:
                self.close()
            self.orderid = self.sell(size=self.p.stake)

cerebro.broker.setcash(1000.0)
cerebro.broker.setcommission(commission=0.0, margin=0.02)
cerebro.broker.set_slippage_perc(perc=0.005)

cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn')

cerebro.addstrategy(DualMovingAverageStrategy)

result = cerebro.run()
strat = result[0]
print("--------------- AnnualReturn -----------------")
print(strat.analyzers._AnnualReturn.get_analysis())

AnReturn = strat.analyzers._AnnualReturn.get_analysis()
df = pd.DataFrame(AnReturn.values(), index=AnReturn.keys()).reset_index()
df.columns=['Year', 'AnnualReturn']
df.to_csv('DemoDMA.csv', index=False)

print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

figure = cerebro.plot(style='candlestick', volume=False,
                      barup = '#ff9896', bardown='#98df8a',
                      tickrotation=10, )[0][0]

figure.savefig('DemoDMA.png')