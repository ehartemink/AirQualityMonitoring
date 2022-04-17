from dash import Dash, html, dcc
from dash.dependencies import Input, Output
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import database

app = Dash(__name__)

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more 
database_path = "persist/table.csv"
db = database.DataBase(database_path)
df = db.open_table()
df_by_metric = {metric: df for (metric, df) in df.groupby("metric")}

def write_graph_id(prefix):
	return f"{prefix}_graph".replace(".", "")

def write_div_id(prefix):
	return f"{prefix}_div".replace(".", "")

def create_graph_div(metric):
	return html.Div(children=[
		html.H2(metric),
		dcc.Graph(
			id=write_graph_id(metric),
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
			marks=dict(enumerate(["1 min", "5 min", "1 hour", "24 hours", "1 week"])),
            value=5,
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

def create_figure(metric, df):
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
	for metric in sorted(df_by_metric.keys()):
		df = df_by_metric[metric]
		seconds_lookback=[60, 300, 3600, 86400, 604800][lookback_window-1]
		df = df[df.timestamp > (dt.datetime.now() - dt.timedelta(seconds=seconds_lookback)).timestamp()]
		output_figures.append(
			create_figure(metric, df)
		)
	return output_figures


if __name__ == '__main__':
    app.run_server(debug=True, host="0.0.0.0", port=8000)
