from dash import Dash, html, dcc
from dash.dependencies import Input, Output
from plotly.subplots import make_subplots
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
from threading import Thread
import database

app = Dash(__name__)

INITIAL_LOOKBACK_WINDOW = 2

database_path = "persist/table.csv"
lookbacks = ["1 min", "5 min", "1 hour", "8 hours", "24 hours"]
lookbacks_in_seconds = {
	"1 min": 60,
	"5 min": 300,
	"1 hour": 3600,
	"8 hours": 3600*8,
	"24 hours": 86400
}

def create_figure(df, lookback):
	start = dt.datetime.now()
	df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}
	print("splitting df by metric: ",  dt.datetime.now() - start)
	metrics = sorted(df_by_metric.keys())
	total_subplots = len(metrics)
	print("total subplots: ", total_subplots)
	fig = make_subplots(rows=(total_subplots+1)//2, cols=2, subplot_titles=metrics)
	start = dt.datetime.now()
	for (i, metric) in enumerate(metrics):
		df = df_by_metric[metric]
		row_idx = (i // 2) + 1
		col_idx = (i % 2) + 1
		try:
			fig.add_scattergl(
			x=df["timestamp"],
			y=df["value"],
			row=row_idx,
			col=col_idx,
			mode="markers",
			marker={"size": 5}
			)
		except Exception as e:
			print("Exception: ", e)
			print(df)
		fig.update_xaxes(title_text="Timestamp", row=row_idx, col=col_idx)
		fig.update_yaxes(title_text=metric, row=row_idx, col=col_idx)
	print("Plotting figure time: ", dt.datetime.now() - start)
	fig.update_layout(height=3000, width=2000)
	return fig

def refresh_figures_cache(db, figures_cache):
	for lookback_window in range(0, 5):
		try:
			start = dt.datetime.now()
			df = db.open_table()
			print("Newest Record: ", dt.datetime.now().timestamp()- df.timestamp.max())
			print("Open table time: ", dt.datetime.now() - start)
			seconds_lookback=lookbacks_in_seconds[lookbacks[lookback_window]]
			start_new = dt.datetime.now()
			df = df[df.timestamp > (dt.datetime.now() - dt.timedelta(seconds=seconds_lookback)).timestamp()]
			print("Filter table time: ", dt.datetime.now() - start_new)
			df.timestamp = [dt.datetime.fromtimestamp(val).strftime("%Y-%m-%d %H:%M:%S") for val in df["timestamp"]]
			fig = create_figure(df, lookback_window)
			figures_cache[lookback_window] = fig
		except Exception as e:
			print("Write figures failed for ", lookbacks[lookback_window])
			print("Exception: ", e)
		print("Write figures cache for ", lookbacks[lookback_window], dt.datetime.now() - start)

def figures_cache_loop(db, figures_cache):
	while True:
		refresh_figures_cache(db, figures_cache)

def write_graph_id(prefix):
	return f"{prefix}_graph".replace(".", "")

def write_div_id(prefix):
	return f"{prefix}_div".replace(".", "")

def create_graph_div(metric):
	return html.Div(children=[
		html.H2(metric),
		dcc.Graph(
			id=write_graph_id(metric),
			figure=figures_cache[INITIAL_LOOKBACK_WINDOW],
			config={
				'displayModeBar': False
			}
		)
	], 
	id=write_div_id(metric),
	style={'width': '49%', 'display': 'inline-block'})
	
db = database.DataBase(database_path)
df = db.open_table()
df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}
figures_cache = database.ThreadSafeDict()
refresh_figures_cache(db, figures_cache)
figures_cache_daemon = Thread(target=figures_cache_loop, name="figures-cache-daemon", args=(db, figures_cache))
figures_cache_daemon.start()

app.layout = html.Div(children=[
    html.H1(children="William Hartemink's Air Quality Monitoring Dashboard"),

	html.Label('Lookback Window'),
		dcc.Slider(
            min=0,
            max=4,
			marks=dict(enumerate(lookbacks)),
            value=INITIAL_LOOKBACK_WINDOW,
			step=1,
			included=False,
			id='lookback-window'
        ),
	html.Div([dcc.Graph(
		id="figure-id",
		config={
                'displayModeBar': False
            }
		)],
		style={'width': '98%', 'display': 'inline-block'}),
	

	dcc.Interval(
            id='interval-component',
            interval=3.5*1000, # in milliseconds
            n_intervals=0)
])



@app.callback(
				Output("figure-id", "figure"),
				Input("lookback-window", "value"),
				Input("interval-component", "n_intervals")
		)
def create_figures(lookback_window, n):
	return figures_cache[lookback_window]
	

if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=8000)
