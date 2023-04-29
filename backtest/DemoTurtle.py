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

class TurtleStrategy(bt.Strategy):
    params = dict(
        N1= 20, # Donchian Channels upper period
        N2=10, # Donchian Channels lower period
        stake = 300,
        )
    def log(self, txt, dt=None):
        dt = dt or self.datas[0].datetime.date(0)
        dtstr = dt.strftime('%Y-%m-%d')
        print('%s, %s' % (dtstr, txt))

    def __init__(self):
        self.close = self.datas[0].close
        self.high = self.datas[0].high
        self.low = self.datas[0].low
        self.DonchianH = bt.ind.Highest(self.high(-1), period=self.p.N1, subplot=False)
        self.DonchianL = bt.ind.Lowest(self.low(-1), period=self.p.N2, subplot=False)
        self.CrossoverH = bt.ind.CrossOver(self.close(0), self.DonchianH, subplot=True)
        self.CrossoverL = bt.ind.CrossOver(self.close(0), self.DonchianL, subplot=True)
        self.TR = bt.ind.Max((self.high(0)-self.low(0)),
                                    abs(self.high(0)-self.close(-1)),
                                    abs(self.low(0)-self.close(-1)))
        self.ATR = bt.ind.SimpleMovingAverage(self.TR, period=self.p.N1, subplot=True)

        self.order=None
        self.last_price = 0
        self.count = 0

    def next(self):
        self.log('C: %.4f, H: %.4f, L: %.4f, DH: %.4f, DL: %.4f, ATR: %.4f' % (\
            self.data0.close[0], self.data0.high[0], self.data0.low[0], self.DonchianH[0], \
                self.DonchianL[0], self.ATR[0]
        ))
        if self.position.size == 0:
            if self.CrossoverH > 0:
                self.order = self.buy(size=self.p.stake)
                self.last_price = self.data0.close[0]
                self.count = 0
                self.log('buy start')
            elif self.CrossoverL < 0:
                self.order = self.sell(size=self.p.stake)
                self.last_price = self.data0.close[0]
                self.count = 0
                self.log('sell start')
        elif self.position.size > 0: # buy position
            if self.CrossoverL < 0: # Take Profit
                self.sell(size=self.position.size)
                self.log('close buy position: Take Profit')
            elif self.data0.close[0] > self.last_price + 0.5*self.ATR[0] and self.count < 3:
                self.order = self.buy(size=self.p.stake)
                self.last_price = self.data0.close[0]
                self.count += 1
                self.log('buy more: %d' % self.count)
            elif self.data0.close[0] < self.last_price - 2*self.ATR[0]: # Stop Loss
                self.sell(size=self.position.size)
                self.log('close buy position: Stop Loss')
        else: # sell position
            if self.CrossoverH > 0: # Take Profit
                self.buy(size=abs(self.position.size))
                self.log('close sell position: Take Profit')
            elif self.data0.close[0] < self.last_price - 0.5*self.ATR[0] and self.count < 3:
                self.order = self.sell(size=self.p.stake)
                self.last_price = self.data0.close[0]
                self.count += 1
                self.log('sell more: %d' % self.count)
            elif self.data0.close[0] > self.last_price + 2*self.ATR[0]: # Stop Loss
                self.buy(size=abs(self.position.size))
                self.log('close sell position: Stop Loss')


cerebro.broker.setcash(1000.0)
cerebro.broker.setcommission(commission=0.0, margin=0.02)
cerebro.broker.set_slippage_perc(perc=0.005)

cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn')

cerebro.addstrategy(TurtleStrategy)

result = cerebro.run()
strat = result[0]
print("--------------- AnnualReturn -----------------")
print(strat.analyzers._AnnualReturn.get_analysis())

AnReturn = strat.analyzers._AnnualReturn.get_analysis()
df = pd.DataFrame(AnReturn.values(), index=AnReturn.keys()).reset_index()
df.columns=['Year', 'AnnualReturn']
df.to_csv('DemoTurtle.csv', index=False)

print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

figure = cerebro.plot(style='candlestick', volume=False,
                      barup = '#ff9896', bardown='#98df8a',
                      tickrotation=10, )[0][0]

figure.savefig('DemoTurtle.png')