#!/usr/bin/env python3
import backtrader as bt
import btoandav20
from datetime import datetime
import json
import csv

class SeizeVolatilityStrategy(bt.Strategy):
    params = (('price_base', 1.0300),
              ('price_unit', 0.0020),
              ('value_unit', 600),
              ('max_unit', 35))
    
    def log(self, txt, dt=None):
        dt = dt or self.data0.datetime.datetime()
        dtstr = dt.strftime('%Y-%m-%d %H:%M:%S')
        self.logfile.write('%s, %s\n' % (dtstr, txt))
        self.logfile.flush()
    
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
                position = self.broker.getserverposition(self.data0, update_latest=True)
                # position = self.broker.getposition(self.data0)
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

cerebro = bt.Cerebro()

with open("config.json", "r") as file:
    config = json.load(file)

storekwargs = dict(
    token=config["oanda"]["token"],
    account=config["oanda"]["account"],
    practice=config["oanda"]["practice"],
)
store = btoandav20.stores.OandaV20Store(**storekwargs)

datakwargs = dict(
    timeframe=bt.TimeFrame.Minutes,
    compression=1,
    qcheck=1.0,
    historical=False,
    fromdate=None,
    bidask=None,
    useask=None,
    backfill_start=False,
    backfill=False,
    tz='America/New_York',
)

data = store.getdata(dataname="EUR_USD", **datakwargs)
cerebro.adddata(data)
cerebro.setbroker(store.getbroker())

cerebro.addstrategy(SeizeVolatilityStrategy)

print('LiveVolatility start...')
cerebro.run()