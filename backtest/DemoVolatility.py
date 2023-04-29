import backtrader as bt
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
plt.rcParams["figure.figsize"] = (15,8)
import csv

cerebro = bt.Cerebro(stdstats=False)
cerebro.addobserver(bt.observers.BuySell)
cerebro.addobserver(bt.observers.Broker)

data = bt.feeds.GenericCSVData(
    dataname='dataMT5/EURUSDM1_220301.csv',
    nullvalue=0.0,
    timeframe=bt.TimeFrame.Minutes, 
    compression=1,
    fromdate=datetime(2023, 3, 1, 9, 45, 00),
    todate=datetime(2023, 4, 22, 00, 00, 00),
    dtformat=('%Y.%m.%d %H:%M'),

    open=1,
    high=2,
    low=3,
    close=4,
    volume=5,
    openinterest=-1
)

cerebro.adddata(data)

class SeizeVolatilityStrategy(bt.Strategy):
    params = (('price_base', 1.0300),
              ('price_unit', 0.0020),
              ('value_unit', 600),
              ('max_unit', 35))
    
    def __init__(self):
        self.logfile = None
        self.csvfile = None
        self.csvwriter = None
        self.order = None
        self.order_time = None
        self.units = 0
        self.new_units = 0
        self.price_position = self.p.price_base - self.p.price_unit * self.units # <0: sell
        self.count = 0
        self.prev_close = None

    def notify_order(self, order):
        order_info = '\n----------ORDER BEGIN----------\n%s\n----------ORDER END----------' % order
        self.log(order_info)
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            self.units = self.new_units
            self.price_position = self.p.price_base - self.p.price_unit * self.units # <0: sell
            position = self.broker.getposition(self.data0)            
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.4f, Cost: %.4f, Position: %.4f' %
                    (order.executed.price,
                     order.executed.value,
                     position.size))

            else:  # Sell
                self.log('SELL EXECUTED, Price: %.4f, Cost: %.4f, Position: %.4f' %
                         (order.executed.price,
                          order.executed.value,
                          position.size))

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        # Write down: no pending order
        self.order = None

    def next(self):
        if self.order:
            if (datetime.now() - self.order_time).total_seconds() > 60: # order time out
                self.log('Order Timeout')
                # position = self.broker.getserverposition(self.data0, update_latest=True)
                position = self.broker.getposition(self.data0)
                self.log('Position size: %d, price: %.4f' % (position.size, position.price))
                self.order = None
                # cheat as order.completed
                self.units = self.new_units
                self.price_position = self.p.price_base - self.p.price_unit * self.units # <0: sell
            return
        
        self.order_time = datetime.now()
            
        str_close = '%.4f' % (self.data0.close[0])
        if str_close != self.prev_close:
            self.log('%s --- %d' % (str_close, self.new_units))
            self.prev_close = str_close
        diff_units = -1 * int((self.data0.close[0] - self.price_position)/self.p.price_unit)
        if diff_units != 0 and abs(self.units+diff_units) <= self.p.max_unit:
            self.count += 1
            self.new_units = self.units + diff_units
            position = self.broker.getposition(self.data0)
            value = self.broker.getvalue()
            cash = self.broker.getcash()
            self.log('count: %d, price: %.4f, unit: %d, value: %.2f, cash: %.2f, posi_size: %d, posi_price: %.4f' % \
                     (self.count, self.data0.close[0], diff_units, value, cash, position.size, position.price))
            self.csvwriter.writerow([self.datetime.datetime().strftime('%Y-%m-%d %H:%M:%S'), \
                                   '%d' % self.count, \
                                   '%.4f' % self.data0.close[0], \
                                   '%d' % diff_units, \
                                   '%.2f' % value, \
                                   '%.2f' % cash, \
                                   '%d' % position.size, \
                                    '%.4f' % position.price])
            self.csvfile.flush()
            if diff_units < 0:
                self.order = self.sell(size=self.p.value_unit*abs(diff_units), price=self.data0.close[0])
            else:
                self.order = self.buy(size=self.p.value_unit*abs(diff_units), price=self.data0.close[0])

    def start(self):
        self.logfile = open('access.log', 'a')
        self.csvfile = open('OandaActivity.csv', 'w')
        self.csvwriter = csv.writer(self.csvfile)
        self.csvwriter.writerow((['datetime', 'count', 'price', 'unit', 'value', 'cash', 'posi_value', 'posi_price']))
        self.done = False
        position = self.broker.getposition(self.data0)
        self.units = int(position.size / self.p.value_unit)
        self.new_units = self.units
        self.price_position = self.p.price_base - self.p.price_unit * self.units # <0: sell
        self.log('Initialization, Position: %d, %.4f, uints: %d' % (position.size, position.price, self.units), 
                 dt=datetime.now())

    def stop(self):
        print('Data length: %d' % (len(self.data0)))
        self.logfile.close()
        self.csvfile.close()

    def log(self, txt, dt=None):
        dt = dt or self.data0.datetime.datetime()
        dtstr = dt.strftime('%Y-%m-%d %H:%M:%S')
        self.logfile.write('%s, %s\n' % (dtstr, txt))
        self.logfile.flush()

cerebro.broker.setcash(1066.0)
cerebro.broker.setcommission(commission=0.0, margin=0.02)
cerebro.broker.set_slippage_perc(perc=0.005)

cerebro.addanalyzer(bt.analyzers.AnnualReturn, _name='_AnnualReturn')

cerebro.addstrategy(SeizeVolatilityStrategy)

result = cerebro.run()
strat = result[0]
print("--------------- AnnualReturn -----------------")
print(strat.analyzers._AnnualReturn.get_analysis())

AnReturn = strat.analyzers._AnnualReturn.get_analysis()
df = pd.DataFrame(AnReturn.values(), index=AnReturn.keys()).reset_index()
df.columns=['Year', 'AnnualReturn']
df.to_csv('DemoVolatility.csv', index=False)

print(f'Final Portfolio Value: {cerebro.broker.getvalue():.2f}')

figure = cerebro.plot(style='candlestick', volume=False,
                      barup = '#ff9896', bardown='#98df8a',
                      tickrotation=10, )[0][0]

figure.savefig('DemoVolatility.png')