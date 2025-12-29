"""
Charts - Componentes de graficos reutilizaveis
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def create_empty_figure(message="Sem dados"):
    """Cria figura vazia com mensagem"""
    fig = go.Figure()
    fig.update_layout(
        template='plotly_dark',
        height=400,
        annotations=[{
            'text': message,
            'xref': 'paper',
            'yref': 'paper',
            'x': 0.5,
            'y': 0.5,
            'showarrow': False,
            'font': {'size': 16, 'color': 'gray'}
        }]
    )
    return fig


def create_time_series(df, x_col, y_col, name='', color='#3498db', fill=False):
    """Cria grafico de serie temporal"""
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df[x_col],
        y=df[y_col],
        name=name,
        mode='lines',
        line=dict(color=color, width=2),
        fill='tozeroy' if fill else None
    ))

    fig.update_layout(
        template='plotly_dark',
        height=400,
        hovermode='x unified'
    )

    return fig


def create_bar_chart(df, x_col, y_col, name='', color='#3498db'):
    """Cria grafico de barras"""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=df[x_col],
        y=df[y_col],
        name=name,
        marker_color=color
    ))

    fig.update_layout(
        template='plotly_dark',
        height=400
    )

    return fig


def create_pie_chart(df, values_col, names_col, title=''):
    """Cria grafico de pizza"""
    fig = px.pie(
        df,
        values=values_col,
        names=names_col,
        title=title,
        template='plotly_dark'
    )

    fig.update_layout(height=400)

    return fig


def create_treemap(df, path_cols, values_col, color_col=None, title=''):
    """Cria treemap"""
    fig = px.treemap(
        df,
        path=path_cols,
        values=values_col,
        color=color_col,
        title=title,
        template='plotly_dark'
    )

    fig.update_layout(height=500)

    return fig


def create_comparison_chart(df, x_col, y_col, group_col, base_100=True):
    """Cria grafico de comparacao de multiplas series"""
    fig = go.Figure()

    for group_name in df[group_col].unique():
        group_data = df[df[group_col] == group_name]

        y_values = group_data[y_col]

        if base_100 and len(y_values) > 0:
            base_value = y_values.iloc[0]
            if base_value and base_value > 0:
                y_values = (y_values / base_value) * 100

        fig.add_trace(go.Scatter(
            x=group_data[x_col],
            y=y_values,
            mode='lines',
            name=group_name
        ))

    if base_100:
        fig.add_hline(y=100, line_dash="dash", line_color="gray")

    fig.update_layout(
        template='plotly_dark',
        height=400,
        hovermode='x unified',
        legend=dict(orientation='h', y=1.1)
    )

    return fig
