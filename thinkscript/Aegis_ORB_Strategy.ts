# Aegis ORB v0.2 - hypothetical strategy for a 5-minute chart.
# thinkScript strategy orders are simulated and do not submit brokerage orders.

declare upper;
input openingRangeEnd = 0945;
input entryCutoff = 1400;
input volumeLookback = 5;
input volumeFactor = 1.20;
input rewardToRisk = 2.0;

rec openingHigh = if GetYYYYMMDD() != GetYYYYMMDD()[1] then high
                  else if SecondsTillTime(openingRangeEnd) > 0 then Max(openingHigh[1], high)
                  else openingHigh[1];
rec openingLow = if GetYYYYMMDD() != GetYYYYMMDD()[1] then low
                 else if SecondsTillTime(openingRangeEnd) > 0 then Min(openingLow[1], low)
                 else openingLow[1];

def dailyVwap = vwap(period = AggregationPeriod.DAY);
def averageVolume = Average(volume[1], volumeLookback);
def inEntryWindow = SecondsFromTime(openingRangeEnd) >= 0 and SecondsTillTime(entryCutoff) >= 0;
def breakout = close crosses above openingHigh;
def volumeConfirmed = volume >= averageVolume * volumeFactor;
def longSignal = inEntryWindow and breakout and close > dailyVwap and volumeConfirmed;
def stopPrice = Min(low, openingHigh);
def targetPrice = close + (close - stopPrice) * rewardToRisk;

plot ORHigh = openingHigh;
plot ORLow = openingLow;
plot DailyVWAP = dailyVwap;

AddOrder(OrderType.BUY_TO_OPEN, longSignal, open[-1], 1, Color.GREEN, Color.GREEN, "ORB Long");
AddOrder(OrderType.SELL_TO_CLOSE, low <= stopPrice, stopPrice, 1, Color.RED, Color.RED, "Stop");
AddOrder(OrderType.SELL_TO_CLOSE, high >= targetPrice, targetPrice, 1, Color.CYAN, Color.CYAN, "Target");
