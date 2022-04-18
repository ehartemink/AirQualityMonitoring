from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
from threading import Thread
import database

app = Dash(__name__)

database_path = "persist/table.csv"
lookbacks = ["1 min", "5 min", "1 hour", "24 hours", "1 week"]
lookbacks_in_seconds = {
	"1 min": 60,
	"5 min": 300,
	"1 hour": 3600,
	"24 hours": 86400,
	"1 week": 604800
}
db = database.DataBase(database_path)
df = db.open_table()
df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}

def create_figure(metric, df, lookback):
	seconds_lookback=lookbacks_in_seconds[lookback]
	df = df[df.timestamp > (dt.datetime.now() - dt.timedelta(seconds=seconds_lookback)).timestamp()]
	fig = go.Figure(data=go.Scattergl(
    	x=df["timestamp"],
    	y=df["value"],
    	mode='markers'
	))

	fig.update_layout(
    	title=metric.upper(),
    	xaxis_title="Time",
    	yaxis_title="Value",
    	legend_title="Legend Title",
    	font=dict(
        	family="Garamond",
        	size=8,
        	color="#1E90FF"
    	)
	)
	return fig

def refresh_figures_cache(metrics, db, figures_cache):
	for metric in metrics:
		df = db.open_table()
		df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}
		df = df_by_metric[metric]
		for lookback in lookbacks:
			fig = create_figure(metric, df, lookback)
			figures_cache[metric + lookback] = fig

def figures_cache_daemon(metrics, db, figures_cache):
	while True:
		refresh_figures_cache(metrics, db, figures_cache)

figures_by_metric_lookback = {metric + lookback: create_figure(metric, df, lookback) for (metric, df) in df_by_metric.items() for lookback in lookbacks}
figures_cache = database.ThreadSafeDict()
refresh_figures_cache(sorted(df_by_metric.keys()), db, figures_cache)
figures_cache_daemon_thread = Thread(target=figures_cache_daemon, args=(sorted(df_by_metric.keys()), db, figures_cache))

def write_graph_id(prefix):
	return f"{prefix}_graph".replace(".", "")

def write_div_id(prefix):
	return f"{prefix}_div".replace(".", "")

def create_graph_div(metric):
	return html.Div(children=[
		html.H2(metric),
		dcc.Graph(
			id=write_graph_id(metric),
			figure=figures_by_metric_lookback[metric + "1 hour"],
			config={
				'displayModeBar': False
			}
		)
	], 
	id=write_div_id(metric),
	style={'width': '49%', 'display': 'inline-block'})
	

app.layout = html.Div(children=[
    html.H1(children='Welcome to my dashboard'),

    html.Div(children='''
        Dash: A web application framework for your data.
    '''),


	html.Label('Lookback Window'),
		dcc.Slider(
            min=0,
            max=4,
			marks=dict(enumerate(lookbacks)),
            value=2,
			step=1,
			included=False,
			id='lookback-window'
        ),
	*[create_graph_div(metric) for metric in sorted(df_by_metric)],

	dcc.Interval(
            id='interval-component',
            interval=15*1000, # in milliseconds
            n_intervals=0)
])

@app.callback(*[
				Output(write_graph_id(metric), 'figure')
				for metric in sorted(df_by_metric.keys())
				],
				Input('lookback-window', 'value'),
				Input('interval-component', 'n_intervals')
			)
def create_figures(lookback_window, n):
	output_figures = []
	df = db.open_table()
	df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}
	output_figures = [figures_cache[metric + lookbacks[lookback_window]] for metric in sorted(df_by_metric.keys())]
	return output_figures

figures_cache_daemon_thread.start()

if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=8000)
