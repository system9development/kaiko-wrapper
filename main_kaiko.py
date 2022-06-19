# -*- coding: utf-8 -*-
"""
Created on Fri Jun 17 22:56:01 2022

@author: rpitc
"""


from dotenv import load_dotenv
import typing
import sys
import os
import re
import glob
import time
import datetime
from tqdm import tqdm
import numpy as np
import pandas as pd

from kaiko import kaiko

load_dotenv(".env")
kaiko_api_key = os.getenv("KAIKO_API_KEY")

kc = kaiko.KaikoClient(api_key=kaiko_api_key)

# ds = kaiko.Aggregates(type_of_aggregate='COHLCV',
#                       exchange='lmax',
#                       instrument = 'btc-usd',
#                       start_time='2020-08',
#                       interval='1d',
#                       client=kc)

# df1 = ds.df

# dref = kaiko.DerivativesReference(exchange="ftxx",
#                                   instrument_class="future",
#                                   client=kc)

# df_ref= dref.df

# drisk = kaiko.DerivativesRisk(exchange="okex",
#                               instrument_class="future",
#                               instrument="btcusd220624",
#                               interval="1d",
#                               client=kc)

# df_risk = drisk.df

interval = "1d"
exchange = "okex"
instrument_class = "future"
instrument = "btcusd220624"

instrument_class = "perpetual-future"
instrument = "btc-usd"

dprice = kaiko.DerivativesPrice(exchange=exchange,
                                instrument_class=instrument_class,
                                instrument=instrument,
                                interval=interval,
                                client=kc)

# dprice = kaiko.DerivativesPrice(exchange="ftx",
#                                 instrument_class="perpetual-future",
#                                 instrument="btc-usd",
#                                 interval="1h",
                                # client=kc)

df_price = dprice.df