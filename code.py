import re
import requests
import json
import csv
import pandas as pd
import datetime

from persiantools.jdatetime import JalaliDate, JalaliDateTime

import math

import matplotlib.pyplot as plt

from matplotlib import cm

# importing index.csv (Shakhes-e kol)
index = pd.read_csv('index.csv')   

# cleaning index data

index['Date'] = index.Date.apply(lambda x: str(x))
index['year'] = index.Date.apply(lambda x: x[0:4])
index['month'] = index.Date.apply(lambda x: x[4:6])
index['day'] = index.Date.apply(lambda x: x[6:8])

index['date'] = index.Date.apply(lambda x: JalaliDate(int(x[0:4]), int(x[4:6]), int(x[6:8])).to_gregorian())
index['jalaliDate'] = index.date.apply(lambda x: JalaliDate.to_jalali(x))



#index

def getStockDetail(stockId: str) -> "stock": #gets details of stocks
    url = "http://www.tsetmc.com/Loader.aspx?Partree=151311&i={}"
    r = requests.get(url.format(stockId))
    
    stock = {"stock id": stockId}
    stock["group name"] = re.findall(r"LSecVal='([\D]*)',", r.text)[0]
    stock["inst id"] = re.findall(r"InstrumentID='([\w\D]*)',", r.text)[0]
    stock["ins code"] = (

        stockId if re.findall(r"InsCode='(\d*)',", r.text)[0] == stockId else 0
    )
    stock["base vol"] = float(re.findall(r"BaseVol=([\.\d]*),", r.text)[0])
                    
    try:
        stock["name"] = re.findall(r"LVal18AFC='([\D]*)',", r.text)
    except:
        return
    try:
        stock["title"] = re.findall(r"Title='([\D]*)',", r.text)
    except:
        return
    try:
        stock["sector P/E"] = float(re.findall(r"sectorPe ='([\.\d])',", r.text)[0]
                           )
    except:
        stock["sector P/E"] = None
    try:
        stock["share count"] = float(re.findall(r"ZTitad ='([\.\d])',", r.text)[0]
                           )
    except: 
        stock["share count"] = None
    try:
        stock["estimated EPS"] = float(re.findall(r"EstimatedEPS ='([\.\d])',", r.text)[0]
                           )
    except:
        stock["estimated EPS"] = None
    #stock["group id"] = groupId
    if stock["name"] == "',DEven='', LSecVal='', CgrValCot='',Flow='',InstrumentID='":
        return False
    return stock

def getStockPriceHistory(stockId): # gets price history of stocks
    url = "http://members.tsetmc.com/tsev2/chart/data/Financial.aspx?i={}&t=ph&a=1"
    r = requests.get(url.format(stockId))
    priceHistoryText = r.text
    priceHistoryList = priceHistoryText.split(";")
    history = list()
    
    for item in priceHistoryList:
        itemList = item.split(",")
        if len(itemList) < 3:
            break
        historyItem = {}
        historyItem["Date"] = itemList[0]
        historyItem["jalaliDate"] = JalaliDate.to_jalali(int(itemList[0][0:4]), 
                                                         int(itemList[0][4:6]), 
                                                         int(itemList[0][6:8]))
        historyItem["greDate"] = datetime.date(int(itemList[0][0:4]), int(itemList[0][4:6]), int(itemList[0][6:8]))
        historyItem["CLOSE"] = int(itemList[6])

        history.append(historyItem)
        
    return history


#ids of 10 selected stocks: Fameli, Foulad, Ptayer, Pkerman, SHpena, SHranol, GHgorji, GHgol
                            # Vbmellat, Vpasar, Sagharb, Slar, Ktabas, Kzoghal, Bkab, Bayka
                            #   Khazar, Khmoharekeh, Rmapna, Rnik  respectively
ids=['35425587644337450', '46348559193224090',
     '41935584690956944', '23214828924506640',
     '7745894403636165', '44013656953678055',
     '31024260997481994', '22299894048845903',
     '778253364357513', '9536587154100457',
     '52220424531578944','61664227282090067',
     '8977369674477111','28291104595448527',
     '70219663893822560','23891830829322971',
     '32821908911812078','39436183727126211',
     '67126881188552864','33854964748757477'] 

# gathering stocks' datails and price history all in a single dataframe, stocks.

allStockData = list()
for i in ids:
    stock = getStockDetail(i)
    if stock == False or stock == None or type(stock) is not dict:
        continue
        
    stock["history"] = getStockPriceHistory(i)
    allStockData.append(stock)
    

jalaliDates = []
greDates = []
names = []
CLOSE = []

stocks = pd.DataFrame()

for item in allStockData:
    for history in item['history']:
        
        jalaliDates.append(history['jalaliDate'])
        greDates.append(history['greDate'])
        names.append(item['name'][1])
        CLOSE.append(history['CLOSE'])
        

stocks['jalaliDate'] = jalaliDates
stocks['greDate'] = greDates
stocks['name'] = names
stocks['CLOSE'] = CLOSE



#stocks

# separating stocks and dropping dates older than index
stockDf=[]
for name in stocks.name.unique():
    stockDf.append(stocks[(stocks['name']==name) & (stocks['jalaliDate'] >= index['jalaliDate'][0])]) 

# stockDf[2] ## for Petayer

# merging each stock data with index data in case the stock would be locked some day 
                                             # and calculating their monthly return. #

for i in range(0,stocks.name.nunique()):
    
    stockDf[i]= stockDf[i].merge(index, on='jalaliDate', how='left').dropna()
    stockDf[i]= stockDf[i].drop_duplicates(['year','month'], keep = 'last')
    stockDf[i]["stockReturn"]= stockDf[i].CLOSE_x.pct_change()
    stockDf[i]["indexReturn"]= stockDf[i].CLOSE_y.pct_change()
    stockDf[i]=stockDf[i].dropna()    
    
    
    

stockDf[2] #Petayer together with index

#calculating betas
beta=[]
sigmaStock=[]
sigmaIndex=[]
for i in range(0,stocks.name.nunique()):
    sigmaIndex.append(math.sqrt(stockDf[i].indexReturn.var()))
    sigmaStock.append(math.sqrt(stockDf[i].stockReturn.var()))
    beta.append(stockDf[i].stockReturn.corr(stockDf[i].indexReturn) * sigmaStock[i]/sigmaIndex[i])
    


#beta

# calculating the average of stocks' monthly return#
avg = []
for i in range(0,stocks.name.nunique()):
    avg.append(stockDf[i]['stockReturn'].mean())

#avg

result = pd.DataFrame({'name':list(stocks.name.unique()), 
                     'beta': beta,
                     'averageReturn' : avg,
                     'eName': ['Fameli', 'Foulad', 'Ptayer', 'Pkerman', 'SHpena', 'SHranol', 'GHgorji','GHgol',
                             'Vbmellat', 'Vpasar', 'Sagharb', 'Slar', 'Ktabas', 'Kzoghal', 'Bkab', 'Bayka',
                               'Khazar', 'Khmoharekeh', 'Rmapna', 'Rnik']})

#result

ax = result.set_index('beta')['averageReturn'].plot(style='o')

def labelPoint(x, y, val, ax):
    a = pd.concat({'x': x, 'y': y, 'val': val}, axis=1)
    for i, point in a.iterrows():
        ax.text(point['x'], point['y'], str(point['val']))
        
labelPoint(result.beta, result.averageReturn, result.eName, ax)
plt.draw()

result.to_latex(buf='table.tex', columns=['name','beta','averageReturn'],
                header=['متوسط ریترن ماهانه','بتا','نام'], caption=("نتایج به دست آمده","نتایج به دست آمده"),
                label="tb1")

