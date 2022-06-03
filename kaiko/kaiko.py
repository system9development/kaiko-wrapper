"""
Kaiko API Wrapper
"""
import logging
from os import environ

import pandas as pd

import kaiko.utils as ut

try:
    from cStringIO import StringIO      # Python 2
except ImportError:
    from io import StringIO

# Base URLs
_BASE_URL_KAIKO_US = 'https://us.market-api.kaiko.io/'
_BASE_URL_KAIKO_EU = 'https://eu.market-api.kaiko.io/'
_BASE_URL_RAPIDAPI = 'https://kaiko-cryptocurrency-market-data.p.rapidapi.com/'  # Not supported yet
_BASE_URLS = dict(us=_BASE_URL_KAIKO_US, eu=_BASE_URL_KAIKO_EU, rapidapi=_BASE_URL_RAPIDAPI)

################################################# API endpoints #######################################
_URL_REFERENCE_DATA_API = 'https://reference-data-api.kaiko.io/v1/'

#### Trade data ####

_URL_TRADE_HISTORICAL_TRADES = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                         '/trades'

#### Order book data ####

_URL_ORDER_BOOK_SNAPSHOTS_FULL = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                 '/snapshots/full'
_URL_ORDER_BOOK_SNAPSHOTS_RAW = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                '/snapshots/raw'
_URL_ORDER_BOOK_SNAPSHOTS_DEPTH = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                  '/snapshots/depth'
_URL_ORDER_BOOK_SNAPSHOTS_SLIPPAGE = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                     '/snapshots/slippage'

_URL_ORDER_BOOK_AGGREGATIONS_FULL = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}' \
                                    '/{instrument}/ob_aggregations/full'
_URL_ORDER_BOOK_AGGREGATIONS_DEPTH = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                     '/ob_aggregations/depth'
_URL_ORDER_BOOK_AGGREGATIONS_SLIPPAGE = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}' \
                                        '/ob_aggregations/depth'

#### Aggregates data ####
_URL_AGGREGATES_OHLCV = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations' \
                          '/ohlcv'
_URL_AGGREGATES_VWAP = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations' \
                       '/vwap'
_URL_AGGREGATES_COHLCV = 'v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations' \
                         '/count_ohlcv_vwap'

#### Pricing and valuation data ####

_URL_PRICING_SPOT_DIRECT_EXCHANGE_RATE = 'v2/data/trades.{data_version}/spot_direct_exchange_rate/{base_asset}/{quote_asset}'
_URL_PRICING_SPOT_EXCHANGE_RATE = 'v2/data/trades.{data_version}/spot_exchange_rate/{base_asset}/{quote_asset}'
_URL_PRICING_VALUATION = 'v2/data/trades.{data_version}/valuation'

#### DEX liquidity data ####

_URL_DEX_LIQUIDITY_EVENTS = 'v2/data/liquidity.{data_version}/events'
_URL_DEX_LIQUIDITY_SNAPSHOTS = 'v2/data/liquidity.{data_version}/snapshots'

#### Risk management data ####

_URL_RISK_VALUE_AT_RISK = 'v2/data/analytics.v2/value_at_risk?bases={bases}&exchanges={exchanges}&quantities={quantities}&quote={quote}&risk_level={risk_level}&' \
                          'start_time={start_time}&end_time={end_time}&sources={sources}'

#### Reference data ####

_URL_DERIVATIVES_REFERENCE = 'v2/data/derivatives.v2/reference'
_URL_DERIVATIVES_RISK = 'v2/data/derivatives.v2/risk'
_URL_DERIVATIVES_PRICE = 'v2/data/derivatives.v2/price'




# Default settings?

def init_param_dict(keys: list, values: dict = None):
    """
    Creates a dictionary filled with `value` and with keys corresponding to `keys`.

    :param keys: List of keys for the dictionary.
    :param values: Dictionary of values to fill (default is `None`).  If the values dictionary contains keys that
                    did not exist in the list `keys`, then it is added to the return dictionary.
    :type values: dict
    :return: Dictionary with `keys` as keys and `value` as values.
    :rtype: dict
    """
    # Initialize with None values
    output = dict(zip(keys, [None for i in keys]))

    # Overwrite default values
    if values is not None:
        for k in values.keys():
            output[k] = values[k]

    return output


class KaikoClient:
    """
    Kaiko Client: extracts API key from environment, sets base URL and constructs headers for API requests.

    In order to change your API key, you can use the setter method for `api_key_input`. `api_key` contains the key
    used by the client and cannot be set.  `api_key` and `headers` are automatically updated when changing
    `api_key_input`.

    Valid `base_url` include 'us', 'eu', and 'rapidapi' (Rapid API no longer supported).
    """

    def __init__(self, api_key: str = '', base_url: str = 'us'):
        assert base_url in ['us', 'eu'], "base_url  needs to be either us or eu"
        self.base_url = _BASE_URLS[base_url]

        self._api_key_input = api_key

        self.headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Api-Key': self.api_key,
        }

    @property
    def api_key(self) -> str:
        """
        Sets the API key from the environment variable $KAIKO_API_KEY if no key is provided.
        :param api_key: (optional) your API key
        :return: API key to be used in the requests
        """
        env = environ.get('KAIKO_API_KEY')
        kaiko_api_key = env or ''
        api_key = self.api_key_input or kaiko_api_key
        return api_key

    @property
    def api_key_input(self):
        return self._api_key_input

    @api_key_input.setter
    def api_key_input(self, newval):
        self._api_key_input = newval
        self.update_headers()

    def update_headers(self) -> dict:
        self.headers = {
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'X-Api-Key': self.api_key,
        }

    def load_catalogs(self):
        """
        Loads
        1) List of instruments -> self.all_instruments
        2) List of exchanges   -> self.all_exchanges
        3) List of assets      -> self.all_assets

        Those are public endpoints which do not require authentication.
        """
        print("Downloading Kaiko's catalog (lists of instruments, exchanges, assets)...")
        logging.info("Downloading catalogs...")

        # List of all instruments
        self.all_instruments = ut.request_df(_URL_REFERENCE_DATA_API + 'instruments')
        # replace None values by 'ongoing'
        self.all_instruments['trade_end_time'] = self.all_instruments['trade_end_time'].apply(lambda x: x or 'ongoing')

        # List of exchanges and assets
        self.all_exchanges = ut.request_df(_URL_REFERENCE_DATA_API + 'exchanges')
        self.all_assets = ut.request_df(_URL_REFERENCE_DATA_API + 'assets')

        print("\t...done! - available under client.all_{instruments, exchanges, assets}")
        logging.info("... catalogs imported!")

    def __repr__(self):
        return "Kaiko Client set up with \n\tBase URL: {}\n\tAPI Key : {}[...]".format(self.base_url, self.api_key[:5])


class KaikoData:
    """
    General data class
    Get query details from the json file as attributes
    For the definition of the endpoint, there are mandatory instrument descriptions (can we get it from API?)

    Attributes (draft)
     - endpoint = base + endpoint
     - params
    """

    def __repr__(self):
        return f"KaikoData setup with\n- URL\n\t {self.url},\n- Required parameters:\n\t{self.req_params}," \
               f"\n- Optional parameters:\n\t{self.params}"

    def __init__(self, endpoint, req_params: dict, params: dict = {}, client=None, pagination=True, extra_args: dict = {}, **kwargs):
        self.client = client or KaikoClient()
        self.endpoint = self.client.base_url + endpoint
        self.params = params
        self.req_params = req_params
        self._form_url()
        self.extra_args = extra_args

        self.pagination = pagination

        # catch parameters given to the class constructor
        self._add_to_params(**kwargs)
        self._add_to_req_params(**kwargs)

        self._form_url()

        logging.info(f"\n\nInitiated data object\n{self.__repr__()}\n")

    def _form_url(self):
        self.url = self.endpoint.format(**self.req_params)

    @staticmethod
    def _format_param_timestamps(params):
        for key in ['start_time', 'end_time']:
            if key in params:
                params[key] = ut.convert_timestamp_to_apiformat(params[key])
        return params

    @property
    def query(self):
        return dict(**self.params, **self.req_params)

    @property
    def params(self):
        return self._format_param_timestamps(self._params)

    @params.setter
    def params(self, params):
        self._params = params

    def _add_to_params(self, **kwargs):
        for key in kwargs:
            if key in self.parameter_space:
                self._params[key] = kwargs[key]

    def _add_to_req_params(self, **kwargs):
        for key in kwargs:
            if key in self.req_params.keys():
                self.req_params[key] = kwargs[key]

    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

    def _request_api(self):
        print("inside requestion api ")
        self.df, self.query_api, self.query_res = ut.request_df(self.url,
                                                return_query = True,
                                                return_res = True,
                                                headers = self.client.headers,
                                                params = self.params,
                                                df_formatter = self.df_formatter,
                                                pagination = self.pagination,
                                                extra_args = self.extra_args,
                                                )
        print("done:", self.df)

    def load_catalogs(self):
        """ Loads catalogs in the client """
        self.client.load_catalogs()


class Trades(KaikoData):
    """
    This endpoint retrieves trades for an instrument on a specific exchange. Trades are sorted 
    by time; ascendingly in v1, descendingly in v2. Note that taker_side_sell can be null in the 
    cases where this information was not available at collection.

    instrument_class is spot by default
    data_version is latest by default

    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination(https://docs.kaiko.com/#pagination).
    data_version	        Yes	        The data version. (v1, v2 ... or latest)
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    exchange	            Yes	        Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class	    Yes	        Instrument class. See Instruments Reference Data Endpoint.
    instrument	            Yes	        Instrument code. See Instruments Reference Data Endpoint.
    page_size	            No	        See Pagination (min: 1, max: 100000, default is 100000).
    start_time	            No	        Starting time in ISO 8601 (inclusive).

    Fields:

    Field	        Description
    timestamp	    The timestamp provided by the exchange.
    trade_id	    Unique trade ID (unique to the exchange). In case the exchange does not provide an ID, we generate it ourselves.
    price	        Price displayed in quote currency.
    amount	        Quantity of asset bought or sold, displayed in base currency.
    taker_side_sell	See Taker Side Sell (https://docs.kaiko.com/#quot-taker_side_sell-quot-explained)
    """

    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100000), data_version: str = 'latest', client: KaikoClient = None, **kwargs):
        # Initialize endpoint required parameters
        self.req_params = dict(commodity='trades',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'start_time,end_time,page_size,continuation_token'.split(',')

        endpoint = _URL_TRADE_HISTORICAL_TRADES

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

class OrderBookSnapshots(KaikoData):
    """
    Full, Raw, Depth, Slippage Order Book Snapshots data.
    
    type_of_ob is Full by default
    data_version is latest by default
    instrument_class is spot by default
    page_size is 100 by default

    ---------------------------------------------------------------------   Full   ---------------------------------------------------------------------
    
    Full Order-book snapshots data
    Gives access to one month of historical 10% order book snapshots. The full endpoint returns 
    all the following order book data: the snapshot itself (bids and asks), the depth of the order book 
    (the cummulative volume of the base asset at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 2%, 
    4%, 6%, 8% and 10% from the mid price), the spread, the mid price and, when the slippage parameter is not empty, 
    the percentage of slippage for a given order size, either calculated from the best bid/ask or calculated from 
    the mid price. All data is returned in descending order.
    
    Parameters :

    Parameter	            Required	Description
    continuation_token  	No	        See Pagination.
    data_version	        Yes	        The data version. (v1, v2 ... or latest)
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    exchange	            Yes	        Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class	    Yes	        Instrument class. See Instruments Reference Data Endpoint.
    instrument          	Yes	        Instrument code. See Instruments Reference Data Endpoint.
    limit_orders        	No	        Number of orders to return on bid and ask side per snapshot. To retreive the best bid/ask, set this parameter to 1 (default: 10)
    page_size	            No	        Number of snapshots to return. See Pagination (default: 10, max: 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	        Starting time in ISO 8601 (inclusive).
    slippage	            No	        Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	        Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    bid_volume_x	    The volume of bids placed within 0 and x% of the midprice.
    ask_volume_x	    The volume of asks placed within 0 and x% of the midprice.
    spread	            The difference between the best bid and the best ask at the time the snapshot was taken.
    mid_price	        The mid price between the best bid and the best ask.
    ask_slippage	    The percentage price slippage for a market buy order placed at the time that the order book snapshot was taken.
    bid_slippage	    The percentage price slippage for a market sell order placed at the time that the order book snapshot was taken.
    asks	            The sell orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to sell, displayed in the base currency. price is displayed in the quote currency.
    bids	            The buy orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to buy, displayed in the base currency. price is displayed in the quote currency.
 
    ---------------------------------------------------------------------   Raw   ---------------------------------------------------------------------

    Identical to Full but only returns the raw snapshots of bids and asks without 
    any additional metrics. The Full specific parameters (such as slippage and slippage_ref) are disabled but won't 
    yield any errors when used. All data is returned in descending order.

    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	See Pagination.
    data_version	        Yes	The data version. (v1, v2 ... or latest)
    end_time	            No	Ending time in ISO 8601 (exclusive).
    exchange	            Yes	Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class	    Yes	Instrument class. See Instruments Reference Data Endpoint.
    instrument          	Yes	Instrument code. See Instruments Reference Data Endpoint.
    limit_orders	        No	Number of orders to return on bid and ask side per snapshot. To retreive the best bid/ask, set this parameter to 1 (default: 10)
    page_size	            No	Number of snapshots to return. See Pagination (default: 10, max: 100).
    sort	                No	Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	Starting time in ISO 8601 (inclusive).
    
    Fields:

    Field	            Description
    poll_timestamp  	The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    asks	            The sell orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to sell, displayed in the base currency. price is displayed in the quote currency.
    bids	            The buy orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to buy, displayed in the base currency. price is displayed in the quote currency.
 
    ---------------------------------------------------------------------   Depth   ---------------------------------------------------------------------
    
    Identical to Full  but only returns metrics on the depth of the order book 
    (the cummulative volume of the base asset at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 
    2%, 4%, 6%, 8% and 10% from the mid price) per snapshot. The Full specific parameters (such as slippage, slippage_ref 
    and limit_orders) are disabled but won't yield any errors when used. All data is returned in descending order.

    data_version is latest by default
    instrument_class is spot by default


    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination.
    data_version	        Yes	        The data version. (v1, v2 ... or latest)
    end_time   	            No	        Ending time in ISO 8601 (exclusive).
    exchange	            Yes	        Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class	    Yes	        Instrument class. See Instruments Reference Data Endpoint.
    instrument	            Yes	        Instrument code. See Instruments Reference Data Endpoint.
    page_size             	No	        Number of snapshots to return data for. See Pagination (default: 10, max: 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time           	No	        Starting time in ISO 8601 (inclusive).

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    bid_volume_x	    The volume of bids placed within 0 and x% of the midprice.
    ask_volume_x	    The volume of asks placed within 0 and x% of the midprice.
 

    ---------------------------------------------------------------------   Slippage   ---------------------------------------------------------------------

    Identical to Full but only returns slippage for a given order size, either 
    calculated from the best bid/ask or calculated from the mid price. The Full and Raw specific parameter limit_orders 
    is disabled but won't yield any errors when used. All data is returned in descending order.

    Parameters:

    Parameter	            Required	Description
    continuation_token  	No	        See Pagination.
    data_version	        Yes	        The data version. (v1, v2 ... or latest)
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    exchange	            Yes	        Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class	    Yes	        Instrument class. See Instruments Reference Data Endpoint.
    instrument	            Yes	        Instrument code. See Instruments Reference Data Endpoint.
    page_size	            No	        Number of snapshots to return data for. See Pagination (default: 10, max: 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	        Starting time in ISO 8601 (inclusive).
    slippage	            No	        Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	        Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    ask_slippage	    The percentage price slippage for a market buy order placed at the time that the order book snapshot was taken.
    bid_slippage	    The percentage price slippage for a market sell order placed at the time that the order book snapshot was taken.

    """

    def __init__(self, exchange: str, instrument: str, type_of_ob: str = 'Full', instrument_class: str = 'spot', params: dict = dict(page_size = 100),
                    data_version: str = 'latest', client: KaikoClient = None, **kwargs):
        # Initialize endpoint required parameters
        assert type_of_ob in ['Full', 'Raw', 'Depth', 'Slippage'], "type_of_ob needs to be either Full, Raw, Depth, Slippage"

        if type_of_ob in ['Full', 'Raw']:
            self.parameter_space = 'continuation_token,end_time,limit_orders,page_size,sort,start_time,slippage,slippage_ref'.split(',')
        else:
            self.parameter_space = 'continuation_token,end_time,page_size,sort,start_time'.slipt(',')
        
        self.extra_args = {'type_of_ob': type_of_ob}

        endpoints = {'Full': _URL_ORDER_BOOK_SNAPSHOTS_FULL, 'Raw': _URL_ORDER_BOOK_SNAPSHOTS_RAW, 'Depth': _URL_ORDER_BOOK_SNAPSHOTS_DEPTH, 'Slippage': _URL_ORDER_BOOK_SNAPSHOTS_SLIPPAGE}
        endpoint = endpoints[type_of_ob]
        self.req_params = dict(commodity = 'order_book_snapshots',
                                data_version = data_version,
                                exchange = exchange,
                                instrument_class = instrument_class,
                                instrument = instrument)

        KaikoData.__init__(self, endpoint, self.req_params, params, client, extra_args = self.extra_args, **kwargs)
        
        self._request_api()
        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')

    @staticmethod
    def df_formatter(res, **kwargs):
        assert kwargs.keys()
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        if kwargs['type_of_ob'] in ['Depth', 'Full']:
            df = add_price_levels(df)
        return df

class OrderBookSnapshotsFull(KaikoData):
    """
    Full Order-book snapshots data
    Gives access to one month of historical 10% order book snapshots. The full endpoint returns 
    all the following order book data: the snapshot itself (bids and asks), the depth of the order book 
    (the cummulative volume of the base asset at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 2%, 
    4%, 6%, 8% and 10% from the mid price), the spread, the mid price and, when the slippage parameter is not empty, 
    the percentage of slippage for a given order size, either calculated from the best bid/ask or calculated from 
    the mid price. All data is returned in descending order.

    data_version is latest by default
    instrument_class is spot by default

    Parameters :

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination(https://docs.kaiko.com/#usage).
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    limit_orders	        No	        Number of orders to return on bid and ask side per snapshot. To retreive the best bid/ask, set this parameter to 1 (default: 10)
    page_size	            No	        Number of snapshots to return. See Pagination (default: 10, max: 100, default is 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	        Starting time in ISO 8601 (inclusive).
    slippage	            No	        Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	        Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.
    

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    bid_volume_x	    The volume of bids placed within 0 and x% of the midprice.
    ask_volume_x	    The volume of asks placed within 0 and x% of the midprice.
    spread	            The difference between the best bid and the best ask at the time the snapshot was taken.
    mid_price	        The mid price between the best bid and the best ask.
    ask_slippage	    The percentage price slippage for a market buy order placed at the time that the order book snapshot was taken.
    bid_slippage	    The percentage price slippage for a market sell order placed at the time that the order book snapshot was taken.
    asks	            The sell orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to sell, displayed in the base currency. price is displayed in the quote currency.
    bids	            The buy orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to buy, displayed in the base currency. price is displayed in the quote currency.
    """

    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.parameter_space = 'continuation_token,end_time,limit_orders,page_size,sort,start_time,slippage,slippage_ref'.split(',')
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        endpoint = _URL_ORDER_BOOK_SNAPSHOTS_FULL

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
### NEEDS TO BE MODIFIED ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        df = add_price_levels(df)
        return df

def add_price_levels(df):
    """
    Raw order book snapshots data


    Add order-book price levels corresponding to amounts given by the API:
     X_volume_Y where X is in {bid, ask} and Y is the price level relative to the midprice:
     0_1 ... 0_9 : 0.1% to 0.9% away from the mid price
     1 ... 10 : 1% to 10% away from the mid price
    """
    for side in ['bid', 'ask']:
        labs = [l for l in df.columns if l.startswith('%s_volume' % side)]
        for lab in labs:
            # calculate the level
            lvl_lab = lab.split('volume')[-1]
            lvl = float('.'.join(lvl_lab.split('_'))) / 100
            # side of the order book
            eps = -1 * (side == 'bid') + 1 * (side == 'ask')

            newlab = '%s_price%s' % (side, lvl_lab)

            df[newlab] = df["mid_price"] * (1 + eps * lvl)
    return df


class OrderBookSnapshotsRaw(KaikoData):
    """
    Identical to Full but only returns the raw snapshots of bids and asks without 
    any additional metrics. The Full specific parameters (such as slippage and slippage_ref) are disabled but won't 
    yield any errors when used. All data is returned in descending order.

    data_version is latest by default 
    instrument_class is spot by default 


    Parameters:

    Parameter	            Required	Description
    continuation_token  	No      	See Pagination(https://docs.kaiko.com/#usage).
    end_time	            No      	Ending time in ISO 8601 (exclusive).
    limit_orders        	No      	Number of orders to return on bid and ask side per snapshot. To retreive the best bid/ask, set this parameter to 1 (default: 10)
    page_size             	No      	Number of snapshots to return. See Pagination (default: 10, max: 100, default is 100).
    sort	                No      	Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time          	No      	Starting time in ISO 8601 (inclusive).
    slippage            	No      	Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref        	No      	Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.
    
    Fields:

    Field	            Description
    poll_timestamp  	The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    asks	            The sell orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to sell, displayed in the base currency. price is displayed in the quote currency.
    bids	            The buy orders in the snapshot. If the limit_oders parameter is used, this will be reflected here. amount is the quantity of asset to buy, displayed in the base currency. price is displayed in the quote currency.
    """
    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.parameter_space = 'continuation_token, end_time, limit_orders, page_size, sort, start_time, slippage, slippage_ref'.split(',')
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        endpoint = _URL_ORDER_BOOK_SNAPSHOTS_RAW

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
#### NEEDS TO BE MODIFIED ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

class OrderBookSnapshotsDepth(KaikoData):
    """
    Identical to Full  but only returns metrics on the depth of the order book 
    (the cummulative volume of the base asset at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 
    2%, 4%, 6%, 8% and 10% from the mid price) per snapshot. The Full specific parameters (such as slippage, slippage_ref 
    and limit_orders) are disabled but won't yield any errors when used. All data is returned in descending order.

    data_version is latest by default
    instrument_class is spot by default


    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    page_size	            No	        Number of snapshots to return data for. See Pagination (default: 10, max: 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	        Starting time in ISO 8601 (inclusive).

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    bid_volume_x	    The volume of bids placed within 0 and x% of the midprice.
    ask_volume_x	    The volume of asks placed within 0 and x% of the midprice.
    """

    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.parameter_space = 'continuation_token,end_time,page_size,sort,start_time'.split(',')
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        endpoint = _URL_ORDER_BOOK_SNAPSHOTS_DEPTH

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
##### NEEDS TO BE MODIFIED ????
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        df = add_price_levels(df)
        return df

class OrderBookSnapshotsSlippage(KaikoData):
    """
    Identical to Full but only returns slippage for a given order size, either 
    calculated from the best bid/ask or calculated from the mid price. The Full and Raw specific parameter limit_orders 
    is disabled but won't yield any errors when used. All data is returned in descending order.

    data_version is latest by default 
    instrument_class is spot by default 

    Parameters: 

    Parameter	            Required	Description
    continuation_token	    No	See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	Ending time in ISO 8601 (exclusive).
    page_size	            No	Number of snapshots to return data for. See Pagination (default: 10, max: 100, default is 100).
    sort	                No	Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	Starting time in ISO 8601 (inclusive).
    slippage	            No	Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.

    Fields:
    Field	            Description
    poll_timestamp	    The timestamp at which the raw data snapshot was taken.
    poll_date	        The date at which the raw data snapshot was taken.
    timestamp	        The timestamp provided by the exchange. null when not provided.
    ask_slippage	    The percentage price slippage for a market buy order placed at the time that the order book snapshot was taken.
    bid_slippage	    The percentage price slippage for a market sell order placed at the time that the order book snapshot was taken.

    """
    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.parameter_space = 'continuation_token,end_time,page_size,sort,start_time'.split(',')
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        endpoint = _URL_ORDER_BOOK_SNAPSHOTS_SLIPPAGE

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
### needs to be modified ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df



#### FORMATTER NEEDS TO BE ADAPTED ! 

class OrderBookAggregationsFull(KaikoData):
    """
    Gives access to one month of historical 10% order book aggregated data. 
    It returns metrics on the average depth of the order book (the cummulative volume of the base asset 
    at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 2%, 4%, 6%, 8% and 10% from the mid price), 
    the average spread, the average mid price and, when the slippage parameter is not empty, the average percentage 
    of slippage for a given order size, either calculated from the best bid/ask or calculated from the mid price for 
    a given interval. For each interval, the aggregates are calculated by taking the average metrics of each snapshot 
    within that interval. For example, the aggregated 1 hour spread is calculated by taking all spreads of each snapshot 
    within an hour and calculating the average. All data is returned in descending order.

    data_version is latest by default
    instrument_class is spot by default

    Parameters:

    Parameter	            Required	Description
    continuation_token  	No	See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	Ending time in ISO 8601 (exclusive).
    interval	            No	Interval period. Default 1h.
    page_size	            No	Number of snapshots to return data for. See Pagination (default: 10, max: 100, default is 100).
    sort	                No	Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	Starting time in ISO 8601 (inclusive).
    slippage	            No	Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.

    Fields:

    Field	            Description
    poll_timestamp	    The timestamp at which the interval begins.
    bid_volume_x	    The average volume of bids placed within 0 and x% of the midprice over a specified interval.
    ask_volume_x	    The average volume of asks placed within 0 and x% of the midprice over a specified interval.
    spread	            The average difference between the best bid and the best ask over a specified interval.
    mid_price	        The average mid price between the best bid and the best ask over a specified interval
    ask_slippage	    The average percentage of price slippage for a market buy order over a specified interval.
    bid_slippage	    The average percentage of price slippage for a market sell order over a specified interval.

    """
    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'continuation_token,end_time,interval,page_size,sort,start_time,slippage,slippage_ref'.split(',')
        endpoint = _URL_ORDER_BOOK_AGGREGATIONS_FULL

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)
        self._request_api()
        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
#### Needs to be changed ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        df = add_price_levels(df)
        return df

class OrderBookAaggregationsDepth(KaikoData):
    """
    Identical to Full but only returns metrics on average the depth of the order book (the cummulative 
    volume of the base asset at 0.1%, 0.2%, 0.3%, 0.4%, 0.5%, 0.6%, 0.7%, 0.8%, 0.9%, 1%, 1.5%, 2%, 4%, 6%, 
    8% and 10% from the mid price) per snapshot. For each interval, the aggregates are calculated by taking 
    the average metrics of each snapshot within that interval. For example, the aggregated 1 hour spread is 
    calculated by taking all spreads of each snapshot within an hour and calculating the average. The Full 
    specific parameters (such as slippage, slippage_ref) are disabled but won't yield any errors when used. 
    All data is returned in descending order.
    
    data_version is latest by default
    instrument_class is spot by default

    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    interval	            No	        Interval period. Default 1h.
    page_size             	No	        Number of snapshots to return data for. See Pagination (default: 10, max: 100, default is 100).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time	            No	        Starting time in ISO 8601 (inclusive).

    Fields:

    Field	        Description
    poll_timestamp	The timestamp at which the interval begins
    bid_volume_x	The average volume of bids placed within 0 and x% of the midprice over a specified interval.
    ask_volume_x	The average volume of asks placed within 0 and x% of the midprice over a specified interval.
    """

    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', type_of_ob: str = 'full',params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version='latest',
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'continuation_token,end_time,interval,page_size,sort,start_time'.split(',')
        endpoint = _URL_ORDER_BOOK_AGGREGATIONS_DEPTH

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)
        self._request_api()
        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
### Needs to be changed ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        df = add_price_levels(df)
        return df

class OrderBookAggregationsSlippage(KaikoData):
    """
    Identical to Full but only returns the average slippage for a given order size, either calculated from the best 
    bid/ask or calculated from the mid price. For each interval, the aggregates are calculated by taking the 
    average metrics of each snapshot within that interval. For example, the aggregated 1 hour spread is calculated 
    by taking all spreads of each snapshot within an hour and calculating the average. All data is returned in 
    descending order.

    data_version is latest by default
    instrument_class is spot by default

    Parameters:

    Parameter	            Required	Description
    commodity	            Yes	The data commodity.
    continuation_token  	No	See Pagination(https://docs.kaiko.com/#pagination).
    data_version        	Yes	The data version. (v1, v2 ... or latest)
    end_time            	No	Ending time in ISO 8601 (exclusive).
    exchange            	Yes	Exchange code. See Exchanges Reference Data Endpoint.
    instrument_class    	Yes	Instrument class. See Instruments Reference Data Endpoint.
    instrument	            Yes	Instrument code. See Instruments Reference Data Endpoint.
    interval            	No	Interval period. Default 1h.
    page_size           	No	Number of snapshots to return data for. See Pagination (default: 10, max: 100).
    sort                	No	Return the data in ascending (asc) or descending (desc) order. Default desc
    start_time          	No	Starting time in ISO 8601 (inclusive).
    slippage            	No	Order size (in quote asset) for which to calculate the percentage of slippage. Default: 0. When null is returned, not enough volume is present on the order book to execute the order.
    slippage_ref	        No	Price point for which to calculate slippage from. Either from the mid price (mid_price) or from the best bid/ask (best). Default: mid_price.

    Fields:

    Field	        Description
    poll_timestamp	The timestamp at which the interval begins.
    ask_slippage	The average percentage of price slippage for a market buy order over a specified interval.
    bid_slippage	The average percentage of price slippage for a market sell order over a specified interval.
    """
    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', type_of_ob: str = 'full',params: dict = dict(page_size=100),
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='order_book_snapshots',
                               data_version='latest',
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'continuation_token,end_time,interval,page_size,sort,start_time'.split(',')
        endpoint = _URL_ORDER_BOOK_AGGREGATIONS_DEPTH

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)
        self._request_api()
        if len(self.df) == 0:
            print(f'No data was found for the time range selected. \n{self.query_api}')
            print('NB: only one month of historical order book snapshots is available from the API. Please setup a '
                  'Data Feed delivery if you are trying to access data older than a month.')
### Needs to be changed ???
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('poll_timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        df = add_price_levels(df)
        return df

class AggregatesOHLCV(KaikoData):
    """
    Retrieves the OHLCV history for an instrument on an exchange. 
    The interval parameter is suffixed with s, m, h or d to specify seconds, minutes, hours or days, 
    respectively. By making use of the sort parameter, data can be returned in ascending asc or descending desc order.

    data_version is latest
    instrument_class is spot 

    Parameters:

    Parameter	            Required	Description
    continuation_token  	No	        See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    interval	            No	        Interval period. Default 1d.
    page_size             	No	        See Pagination (min: 1, max: 100000, default: 100000).
    start_time           	No	        Starting time in ISO 8601 (inclusive).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default desc

    Fields:

    Field	    Description
    timestamp	Timestamp at which the interval begins.
    open	    Opening price of interval. null when no trades reported.
    high	    Highest price during interval. null when no trades reported.
    low	        Lowest price during interval. null when no trades reported.
    close	    Closing price of interval. null when no trades reported.
    volume	    Volume traded in interval. 0 when no trades reported.
    """
    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100000), 
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='trades',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )
        print("req_params initiliazed")

        self.parameter_space = 'continuation_token,end_time,interval,page_size,start_time,sort'.split(',')
        endpoint = _URL_AGGREGATES_OHLCV
        print("endpoint is done")

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)
        print("requesting api")
        self._request_api()
        print("api request done")
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

class AggregatesVWAP(KaikoData):
    """
    Retrieves aggregated VWAP (volume-weighted average price) history for an instrument on an exchange. The interval 
    parameter is suffixed with s, m, h or d to specify seconds, minutes, hours or days, respectively. By making use 
    of the sort parameter, data can be returned in ascending asc or descending desc (default) order.

    data_version is latest by default
    instrument_class is spot by default 

    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    interval            	No	        Interval period. Default 1d.
    page_size	            No	        See Pagination (min: 1, max: 100000, default is 100000).
    start_time	            No      	Starting time in ISO 8601 (inclusive).
    sort	                No      	Return the data in ascending (asc) or descending (desc) order. Default desc

    Fields: 

    Field	Description
    timestamp	Timestamp at which the interval begins.
    price	Volume-weighted average price. null when no trades reported.
    """

    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100000), 
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='trades',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'continuation_token,end_time,interval,page_size,start_time,sort'.split(',')
        endpoint = _URL_AGGREGATES_VWAP

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

class AggregatesCOHLCV(KaikoData):
    """
    Retrieves the trade count, OHLCV and VWAP history for an instrument on an exchange. The interval parameter is 
    suffixed with s, m, h or d to specify seconds, minutes, hours or days, respectively. By making use of the sort parameter, 
    data can be returned in ascending asc (default) or descending desc order.

    data_version is latest by default
    instrument_class is spot by default

    Parameters:

    Parameter	            Required	Description
    continuation_token  	No	See Pagination(https://docs.kaiko.com/#pagination).
    end_time	            No	Ending time in ISO 8601 (exclusive).
    interval	            No	Interval period. Default 1d.
    page_size	            No	See Pagination (min: 1, max: 100000, default is 100000).
    start_time	            No	Starting time in ISO 8601 (inclusive).
    sort	                No	Return the data in ascending (asc) or descending (desc) order. Default desc

    Field	    Description
    timestamp	Timestamp at which the interval begins.
    count	    Then number of trades. 0 when no trades reported.
    open	    Opening price of interval. null when no trades reported.
    high	    Highest price during interval. null when no trades reported.
    low	        Lowest price during interval. null when no trades reported.
    close	    Closing price of interval. null when no trades reported.
    volume	    Volume traded in interval. 0 when no trades reported.
    """


    def __init__(self, exchange: str, instrument: str, instrument_class: str = 'spot', params: dict = dict(page_size=100000), 
                data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(commodity='trades',
                               data_version=data_version,
                               exchange=exchange,
                               instrument_class=instrument_class,
                               instrument=instrument,
                               )

        self.parameter_space = 'continuation_token,end_time,interval,page_size,start_time,sort'.split(',')
        endpoint = _URL_AGGREGATES_COHLCV

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df


## base assset, data_version, quote_asset
class PricingSpotDirectExchangeRate(KaikoData):
    """
    Generates an aggregated price for an asset pair across all exchanges with spot markets for the 
    pair. Only asset combinations which are actively being traded on one of our covered exchanges 
    are being taken into account for the calculation of the price. Unsupported asset 
    combinations will return no data. To return data used as input for the calculation of the 
    aggregated price, set the sources parameter to true. 
    Setting the sources parameter to false (default) will yield a faster response time. 
    By making use of the sort parameter, data can be returned in ascending asc or descending 
    desc order (default).

    data_version is latest by default

    Parameters:

    Parameter	            Required	Description
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    exclude_exchanges	    No	        List of exchanges' code to exclude from the calculation. See Instruments Reference Data Endpoint. Only available in API v2.
    interval	            No	        Interval period. Default 1d.
    include_exchanges	    No	        List of exchanges' code to include in the calculation. See Instruments Reference Data Endpoint. Only available in API v2.
    page_size	            No	        See Pagination (min: 1, max: 1000, default is 1000).
    start_time	            No	        Starting time in ISO 8601 (inclusive).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default is asc in API v1, desc in API v2.
    sources 	            No	        boolean. If true, returns all prices which were used to calculate aggregated price. Default is false
    
    Field	    Description
    timestamp	Timestamp at which the interval begins.
    price	    Aggregated VWAP. null when no trades reported.
    volume	    Total volume traded in interval. 0 when no trades reported.
    count	    Total amount of trades reported during interval. 0 when no trades reported.
    sources     Sources for the prices (if included)
    """
    def __init__(self, base_asset: str, quote_asset: str, params: dict = dict(page_size=1000), data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(data_version=data_version,
                                base_asset=base_asset,
                                quote_asset=quote_asset,
                               )

        self.parameter_space = 'end_time,exclude_exchanges,interval,include_exchanges,page_size,start_time,sort,sources'.split(',')
        endpoint = _URL_PRICING_SPOT_DIRECT_EXCHANGE_RATE

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()
### needs to be adapted ? 
    @staticmethod
    def df_formatter(res, **kwargs):
        data_ = res['data']
        if len(data_) == 0:
            return pd.DataFrame()
        if 'sources' in data_[0].keys(): ## hacky solution for now
            data_ = format_sources_pricing(data_)
        df = pd.DataFrame(data_, dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

def format_sources_pricing(data_):
    data_points = []
    for data_point in data_:
        sources = data_point['sources']
        base_for_df = []
        for pair in sources.keys():
            for k in range(len(sources[pair]['data'])):
                exchange_rate = sources[pair]['data'][k] 
                exchange_rate['pair'] = pair
                base_for_df.append(exchange_rate)
            final_price = sources[pair]['price']
            base_for_df.append({"pair": pair, "exchange_code": "", "count": 0., "price": final_price, "volume": 0.})
        data_points.append(pd.DataFrame(base_for_df))
    for k in range(len(data_)):
        data_[k]['sources'] = data_points[k]
    return data_


## outliers_strategy
## outliers_min_data
## outliers_threshold

class PricingSpotExchangeRate(KaikoData):
    """
    Returns the price of any asset quoted in a Fiat currency within Open Exchange Rate. 
    The USD price is calculated based on the path of the highest liquidity, with an additional 
    step using forex rates to get the final fiat price. This means that, even though an asset 
    might trade directly against all Open Exchange Rate currencies, the price might still be 
    established by using cross-rates1. In cases where the most liquid path changed over time, 
    this will be taken into account in the calculation of the price for each interval. To have an 
    overview of what data was used to calculate the price, set the sources parameter to true. 
    Setting the sourcesparameter to false (default) will yield a faster response time. 
    By making use of the sort parameter, data can be returned in ascending asc (default) or 
    descending desc order.

    data_version is latest by default

    AVAILABLE ONLY WITH V2.

    Parameters:

    Parameter	            Required	Description
    end_time	            No	        Ending time in ISO 8601 (exclusive).
    exclude_exchanges	    No	        List of exchanges' code to exclude from the calculation. See Instruments Reference Data Endpoint. Only available in API v2.
    interval	            No	        Interval period. Default 1d.
    include_exchanges	    No	        List of exchanges' code to include in the calculation. See Instruments Reference Data Endpoint. Only available in API v2.
    outliers_strategy	    No	        Either median_perc, modified_zscore or zscore. See the Outlier Management section below.
    outliers_min_data	    No	        Number of minimum data points needed to trigger the outlier detecton. Default to 4.
    outliers_threshold	    No	        Threshold to use. Usage depends on the chosen outlier management strategy.
    page_size	            No	        See Pagination (min: 1, max: 1000, default is 1000).
    start_time	            No	        Starting time in ISO 8601 (inclusive).
    sort	                No	        Return the data in ascending (asc) or descending (desc) order. Default is asc
    sources     	        No	        boolean. If true, returns all prices which were used to calculate aggregated price. Default is false


    Field	    Description
    timestamp	Timestamp at which the interval begins.
    price	    Aggregated VWAP. null when no trades reported.
    volume	    Total volume traded in interval. 0 when no trades reported.
    count	    Total amount of trades reported during interval. 0 when no trades reported.

    """
    def __init__(self, base_asset: str, quote_asset: str, params: dict = dict(page_size=1000), data_version: str = 'latest', client: KaikoClient = None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(data_version=data_version,
                                base_asset=base_asset,
                                quote_asset=quote_asset,
                               )

        self.parameter_space = 'end_time,exclude_exchanges,interval,include_exchanges,outliers_strategy,outliers_min_data,outliers_threshold,page_size,start_time,sort,sources'.split(',')
        endpoint = _URL_PRICING_SPOT_EXCHANGE_RATE

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

    @staticmethod
    def df_formatter(res, **kwargs):
        data_ = res['data']
        if len(data_) == 0:
            return pd.DataFrame()
        if 'sources' in data_[0].keys(): ## hacky solution for now
            data_ = format_sources_pricing(data_)
        df = pd.DataFrame(data_, dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df


class PricingValuation(KaikoData):
    """
    Allows you to build completely customizable single-asset or multi-asset price feeds for NAV 
    calculations, portfolio valuation, asset allocation strategies, and indices.

    data_version is latest by default
    
    Parameters:

    Parameter	            Required	Description
    continuation_token	    No	        See Pagination.
    end_time	            No	        Last fixing of the calculation in ISO 8601 (exclusive).
    exchanges	            No	        List of exchanges to source data from. See Instruments Reference Data Endpoint. Default: all exchanges
    interval	            No	        Frequency in time unit after the first fixing. Default: 1d.
    percentages	            Yes	        List of percentages for outlier management. To not enforce any outlier management, use 1
    start_time	            No	        First fixing of the calculation in ISO 8601 (inclusive).
    semi_length_window	    Yes	        The time interval to compute the transaction.
    sources	                No	        boolean. If true, returns all prices and volumes which were used to calculate valuation price. Default: false
    quote	                Yes	        The fiat pricing currency.
    weights	                Yes	        Weighting list of base assets. For single-asset price feeds use an asset weighting of “1”
    
    Fields:

    Field	        Description
    timestamp	    Timestamp at which the interval begins.
    percentage	    Percent of the price distribution centered around the median price.
    price	        The composite price, with a base of 100.
    pair	        The constituent pair.
    contribution	The asset contribution to the composite price.
    ref_price	    The reference price per asset.
    weight	        The weight per asset.


    Computation and Constraints

    Considering the volume of data points processed for the computation of each data point, some parameter constraints have been implemented 
    in order to optimize computation time:

    The number of bases must be less or equal to 5
    The number of percentages must be less or equal to 5
    weights and bases must have the same length
    The order of bases and their respective weighting must match
    weights must sum up to 1
    Each response will only contain maximum 7 days of data. To get more data, the continuation_token should be used.
    The interval must be greater than twice the semi_length_window
    
    """
    def __init__(self, bases: list[str], semi_length_window: str, percentages: list[str], quote: str, weights: list[str],params: dict = dict(page_size=100000), data_version: str = 'latest', client: KaikoClient = None, **kwargs):
        assert len(bases) >= 1 and len(bases) <= 5, "Bases needs to have at least one element and maximum 5"
        assert len(bases) == len(weights), "Bases and length are not of the same weight"
        assert len(percentages) <= 5, "Number of percentages must be les or equal to 5"
        # Initialize endpoint required parameters
        self.req_params = dict(data_version=data_version,
                                bases=bases,
                                semi_length_window=semi_length_window,
                                percentages=percentages,
                                quote=quote,
                                weights=weights,
                               )

        self.parameter_space = 'continuation_token,end_time,exchanges,interval,start_time,sources'.split(',')
        endpoint = _URL_PRICING_VALUATION

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()

    @staticmethod
    def df_formatter(res, **kwargs):
        data_ = res['data']
        if len(data_) == 0:
            return pd.DataFrame()
        if 'sources' in data_[0].keys(): ## hacky solution for now
            data_ = format_sources_valuation(data_)
        
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

### needs to be adapted 
def format_sources_valuation(data_):
    return data_


class DEXLiquidityEvents(KaikoData):
    """
    Liquidity events provides flows data about the mint & the burn (adds & removals) type transactions associated to 
    tokens amounts registered on DEXs liquidity pools. This data is made available at a transactional level and at a block granularity.

    Parameter	        Required	Description	                                                                        Example
    exchange	        No	        Should be one of the currently supported DEX	                                    usp2
    pool	            No	        Pool address related to the liquidity event. Default: all liquidity pools.	        0x14de8287adc90f0f95bf567c0707670de52e3813
    pool_contains	    No      	Liquidity events including the requested token. Default: all available tokens.	    weth or weth,usdt,usdc
    block	            No	        Block height.	                                                                    129876
    start_time	        No	        Starting time in ISO 8601 (inclusive)	                                            2022-04-01T00:00:00.000Z
    end_time	        No	        Ending time in ISO 8601 (inclusive)	                                                2022-05-01T00:00:00.000Z
    sort	            No	        Returns the data in ascending (asc) or descending (desc) order. Default: desc.	    asc
    type	            No	        Event type. By default both burn and mint are shown.	                            burn or mint
    """
    def __init__(self, params: dict = dict(page_size=100000), data_version='latest', client=None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(data_version=data_version)

        self.parameter_space = 'exchange,pool,pool_contains,block,start_time,end_time,sort,type'.split(',')
        endpoint = _URL_DEX_LIQUIDITY_EVENTS

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()
    ##needs to be adapted 
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df

class DEXLiquiditySnapshots(KaikoData):
    """
    The liquidity snapshots endpoint provides the total amount of reserves per token, made available at 
    a liquidity pool level for all the covered DEXs. Specifically for Uniswap V3, this data is also made 
    available in a per tick level, and enables the users to visualise the distribution of liquidity across ticks, 
    for every block and liquidity pool available on Uniswap V3.

    Parameter	    Required	Description	                                                                    Example
    pool_address	Yes	        Pool address related to the liquidity event.	                                0x14de8287adc90f0f95bf567c0707670de52e3813
    start_block	    No	        Starting block height.	                                                        129876
    end_block	    No	        Ending block height.	                                                        129886
    start_time	    No	        Starting time in ISO 8601 (inclusive).	                                        2022-04-01T00:00:00.000Z
    end_time	    No	        Ending time in ISO 8601 (inclusive).	                                        2022-05-01T00:00:00.000Z
    sort	        No	        Returns the data in ascending (asc) or descending (desc) order. Default: desc.	asc    
    """
    def __init__(self, pool_address, params: dict = dict(page_size=100000), data_version='latest', client=None, **kwargs):

        # Initialize endpoint required parameters
        self.req_params = dict(data_version=data_version,
                                pool_address=pool_address)

        self.parameter_space = 'start_block,end_block,start_time,end_time,sort'.split(',')
        endpoint = _URL_DEX_LIQUIDITY_EVENTS

        KaikoData.__init__(self, endpoint, self.req_params, params, client, **kwargs)

        self._request_api()
    ##needs to be adapted 
    @staticmethod
    def df_formatter(res, **kwargs):
        df = pd.DataFrame(res['data'], dtype='float')
        df.set_index('timestamp', inplace=True)
        df.index = ut.convert_timestamp_unix_to_datetime(df.index)
        return df



### needs to be changed 





if __name__ == '__main__':
    FORMAT = "%(asctime)-15s %(levelname)-8s | %(lineno)d %(filename)s: %(message)s"
    logging.basicConfig(filename='/var/tmp/kaiko.log', level=logging.DEBUG, format=FORMAT, filemode='a')
    # test = OrderBookAverages('cbse', 'btc-usd', start_time='2020-08-06', interval='10m')

    test = AggregatesOHLCV('cbse', 'eth-usd', start_time='2020-08-06', interval='1d')
    print(test.df)
