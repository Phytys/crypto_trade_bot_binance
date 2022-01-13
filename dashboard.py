import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import dash_table
import plotly.graph_objs as go
from plotly.subplots import make_subplots

from binance.client import Client 
from binance.enums import *

import pandas as pd
import pandas_ta as pta
from datetime import date, datetime, timedelta
import pickle
from collections import ChainMap

import config # config file with API keys


# saved by Trade bot, read csv
TRADE_BOT_CSV = "kline_5m_ETHUSDT.csv"
asset = TRADE_BOT_CSV[9:12]

datatable_cols_binance = ["asset", "free", "locked"]

# NOTE Graph automatically updated from callback/ wrapper

# DASH APP
############################################################################

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

colors = {
    'background': '#ffffff',
    'text': '#002266'
}

app.layout = html.Div(style={'backgroundColor': colors['background']}, children=[
    html.H1(children='[ My Trading Bot ]', style={
            'textAlign': 'center',
            'color': colors['text']
            }
            ),
    html.Div([
            dcc.Graph(id='graph-1',style={"margin-bottom": "0px"} ),
            dcc.Interval(
                id='interval-component-1',
                interval=1*30_000,  # in milliseconds
                n_intervals=0
            )
        ], className="twelve columns"),
    html.Div([
            dcc.Graph(id='graph-2a'),
             dcc.Interval(
                id='interval-component-2a',
                interval=1*30_000,  # in milliseconds
                n_intervals=0
            )
        ], className="three columns"),
    html.Div([
            dcc.Graph(id='graph-2b'),
             dcc.Interval(
                id='interval-component-2b',
                interval=1*30_000,  # in milliseconds
                n_intervals=0
            )
        ], className="four columns"),
    html.Div([
            dcc.Graph(id='graph-2c'),
             dcc.Interval(
                id='interval-component-2c',
                interval=1*30_000,  # in milliseconds
                n_intervals=0
            )
        ], className="three columns"),

    html.Div([
            html.H5(children='Binance Account balance', style={
            'textAlign': 'center',
            'color': colors['text']
            }
            ),
        ], className="six columns"),
    html.Div([
           dash_table.DataTable(
            id='table-paging-and-sorting-bin',
            columns=[
                {'name': i, 'id': i, 'deletable': True} for i in datatable_cols_binance
            ],
            page_current=0,
            page_size=10,
            page_action='custom',

            sort_action='custom',
            sort_mode='single',
            sort_by=[]
            ),
            dcc.Interval(
                id='interval-component-3',
                interval=1*120_000,  # in milliseconds
                n_intervals=0
            )
        ], className="eight columns"),
])


##### Indicators ###

@app.callback(
    Output('graph-2a', 'figure'),
    [Input('interval-component-2a', 'n_intervals')]
)
def tot_balance_indicator(n_clicks):

    # OPEN current balances  droped by bot, coins on index 1
    coins = pickle.load( open( "data/current_balance.p", "rb" ))[1]
    
    fig = go.Figure(go.Indicator(
    mode = "number",
    value = coins,
    number = {'prefix': f"{asset} ", "font":{"size":50}},
    title = {"text": "Num coins"},
    domain = {'x': [0, 1], 'y': [0, 1]}))

    return fig


@app.callback(
    Output('graph-2b', 'figure'),
    [Input('interval-component-2b', 'n_intervals')]
)
def tot_balance_indicator(n_clicks):

    # OPEN DF saved by Bot
    df = pd.read_csv(f"data/{TRADE_BOT_CSV}")
    df["c"] = df["c"].astype(float)
    df["T"] = pd.to_datetime(df["T"], unit="ms")
    df = df.set_index("T")
    last_close = df.c[-1]

    # OPEN current balances saved by bot, plus start capital droped by bot on index 2
    current_balances = pickle.load( open( "data/current_balance.p", "rb" ))
    total_balance = current_balances[0] + (current_balances[1] * last_close)
    start_capital = current_balances[2]

    fig = go.Figure(go.Indicator(
    mode = "number+delta",
    value = total_balance,
    number = {'prefix': "$", "font":{"size":70}},
    title = {"text": "Current total balance"},
    delta = {'position': "top", 'reference': start_capital},
    domain = {'x': [0, 1], 'y': [0, 1]}))

    return fig


@app.callback(
    Output('graph-2c', 'figure'),
    [Input('interval-component-2c', 'n_intervals')]
)
def tot_balance_indicator(n_clicks):

    # OPEN current balances  droped by bot, coins on index 0
    usdt = pickle.load( open( "data/current_balance.p", "rb" ))[0]
    
    fig = go.Figure(go.Indicator(
    mode = "number",
    value = usdt,
    number = {'prefix': "USDT ", "font":{"size":50}},
    title = {"text": "Num USDT"},
    domain = {'x': [0, 1], 'y': [0, 1]}))

    return fig



##### PLOT price action together with Buys and Sells ###
@app.callback(
    Output('graph-1', 'figure'),
    [Input('interval-component-1', 'n_intervals')]
)
def chart(n_clicks):
    # OPEN DF saved by Bot
    df = pd.read_csv(f"data/{TRADE_BOT_CSV}")
    df["c"] = df["c"].astype(float)
    df["T"] = pd.to_datetime(df["T"], unit="ms")
    df = df.set_index("T")
    last_close = df.c[-1]

    #df["rsi_14"] = talib.RSI(df["c"], 14)
    df["rsi_14"] = pta.rsi(df["c"], length=14)
    df["rsi_7"] = pta.rsi(df["c"], length=7)

    df["ma19"] = df["c"].rolling(window=19).mean()
    df["ma50"] = df["c"].rolling(window=50).mean()
    df["ma140"] = df["c"].rolling(window=140).mean()

    # OPEN SELLS saved by bot
    sells = pickle.load( open( "data/sells.p", "rb" ))
    sells_df = pd.DataFrame.from_dict(ChainMap(*sells), orient='index', columns=["sells"])
    sells_df.index = pd.to_datetime(sells_df.index, unit="ms")
    sells_df["sells"] = sells_df["sells"].astype(float)

    # OPEN BUYS saved by bot
    buys = pickle.load( open( "data/buys.p", "rb" ))
    buys_df = pd.DataFrame.from_dict(ChainMap(*buys), orient='index', columns=["buys"])
    buys_df.index = pd.to_datetime(buys_df.index, unit="ms")
    buys_df["buys"] = buys_df["buys"].astype(float)

    # OPEN balances_usdt_lst saved by bot
    balances_usdt = pickle.load( open( "data/balances_usdt_lst.p", "rb" ))
    balances_usdt_df = pd.DataFrame.from_dict(ChainMap(*balances_usdt), orient='index', columns=["balances_usdt"])
    balances_usdt_df.index = pd.to_datetime(balances_usdt_df.index, unit="ms")
    balances_usdt_df["balances_usdt"] = balances_usdt_df["balances_usdt"].astype(float)

    # OPEN balances_coin_lst saved by bot
    balances_coin = pickle.load( open( "data/balances_coin_lst.p", "rb" ))
    balances_coin_df = pd.DataFrame.from_dict(ChainMap(*balances_coin), orient='index', columns=["balances_coin"])
    balances_coin_df.index = pd.to_datetime(balances_coin_df.index, unit="ms")
    balances_coin_df["balances_coin"] = balances_coin_df["balances_coin"].astype(float)

    # JOIN BUY/SELL DFs
    if len(sells) > 0:
        df = df.join(sells_df)
    if len(buys) > 0:
        df = df.join(buys_df)
    if len(balances_usdt) > 0:
        df = df.join(balances_usdt_df)
    if len(balances_coin) > 0:
        df = df.join(balances_coin_df)
    if len(balances_usdt) > 0 and len(balances_coin) > 0:
        df["total_balance"] = df["balances_usdt"] + df["balances_coin"]

    # PLOT
    fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.02,
    specs=[[{"secondary_y": True, 'rowspan': 1}], [{"secondary_y": True}]],
    row_heights=[2.5,0.5],
    subplot_titles=[f"Trading pair: <b>{df.s[-1]}</b>, Price: {last_close}",
     ""]
    )
    fig.add_trace(go.Candlestick(x=df.index,
                    open=df['o'], high=df['h'], low=df['l'], close=df['c']), secondary_y=False,
    )
    if len(sells) > 0:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["sells"],mode="markers", name="sells", line=dict(color='red', width=1), marker=dict(
                    color='red', size=15)), secondary_y=False, row=1, col=1
        )
    if len(buys) > 0:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["buys"],mode="markers", name="buys", line=dict(color='green', width=1), marker=dict(
                    color='green', size=15)), secondary_y=False, row=1, col=1
        )
    if len(balances_usdt) > 0 and len(balances_coin) > 0:
        fig.add_trace(
            go.Scatter(x=df.index, y=df["total_balance"], name="Account Balance", line=dict(color='black', width=2),
            mode="lines+markers", connectgaps=True),
            secondary_y=True, row=1, col=1
        )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["ma19"], name="ma19", mode="lines", line=dict(color='grey', width=1)),
        secondary_y=False, row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["ma50"], name="ma50", line=dict(color='blue', width=1)),
        secondary_y=False, row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["ma140"], name="ma140", line=dict(color='red', width=1)),
        secondary_y=False, row=1, col=1
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=df["rsi_14"], name="rsi_14", line=dict(color='grey', width=1)),
        secondary_y=False, row=2, col=1
    )
    fig.update_layout(xaxis_rangeslider_visible=False)
    # Set y-axes titles
    fig.update_yaxes(title_text="Value", secondary_y=False, color="green")
    fig.update_yaxes(title_text="Account balance", secondary_y=True, color="black")

    return fig

### Account balance from Binance
@app.callback(
    Output('table-paging-and-sorting-bin', 'data'),
    Input('table-paging-and-sorting-bin', "page_current"),
    Input('table-paging-and-sorting-bin', "page_size"),
    Input('table-paging-and-sorting-bin', 'sort_by'),
    Input('interval-component-3', 'n_intervals'))

def account_balance(page_current, page_size, sort_by, n_clicks):

    ## Get account balance from API
    client = Client(config.API_KEY, config.API_SECRET)
    account = client.get_account()
    balances = account["balances"]
    df = pd.DataFrame(balances)
    df["free"] = df["free"].astype(float)
    df = df[df["free"] > 0].sort_values("free", ascending=False)

    if len(sort_by):
        dff = df.sort_values(
            sort_by[0]['column_id'],
            ascending=sort_by[0]['direction'] == 'asc',
            inplace=False
        )
    else:
        # No sort is applied
        dff = df.copy()

    return dff.iloc[
        page_current*page_size:(page_current+ 1)*page_size
    ].to_dict('records')



if __name__ == '__main__':
    app.run_server(debug=True)
