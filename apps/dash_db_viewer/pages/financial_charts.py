"""
Financial Charts - Graficos de dados financeiros
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

from database import financial_queries


def layout():
    """Layout dos graficos financeiros"""
    return html.Div([
        html.H2([
            html.I(className="fas fa-chart-line me-2"),
            "Financial Dashboard"
        ], className="mb-4"),

        # Filtros
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Fundo:"),
                        dcc.Dropdown(
                            id='fund-dropdown',
                            placeholder="Selecione um fundo...",
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Periodo:"),
                        dcc.DatePickerRange(
                            id='date-range',
                            display_format='DD/MM/YYYY',
                            start_date_placeholder_text='Data inicial',
                            end_date_placeholder_text='Data final'
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Presets:"),
                        dbc.ButtonGroup([
                            dbc.Button("1M", id='btn-1m', color="outline-secondary", size="sm"),
                            dbc.Button("3M", id='btn-3m', color="outline-secondary", size="sm"),
                            dbc.Button("6M", id='btn-6m', color="outline-secondary", size="sm"),
                            dbc.Button("1A", id='btn-1a', color="outline-secondary", size="sm"),
                            dbc.Button("YTD", id='btn-ytd', color="outline-secondary", size="sm"),
                            dbc.Button("MAX", id='btn-max', color="outline-primary", size="sm"),
                        ])
                    ], width=4)
                ])
            ])
        ], className="mb-4"),

        # Graficos
        dbc.Row([
            # Grafico principal: PL e Cota
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-chart-area me-2"),
                        "Patrimonio Liquido e Cota"
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='nav-chart', config={'displayModeBar': True}),
                            type="circle"
                        )
                    ])
                ])
            ], width=12, className="mb-4"),
        ]),

        dbc.Row([
            # Movimentacoes
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-exchange-alt me-2"),
                        "Entradas e Saidas"
                    ]),
                    dbc.CardBody([
                        dcc.Loading(
                            dcc.Graph(id='flow-chart', config={'displayModeBar': True}),
                            type="circle"
                        )
                    ])
                ])
            ], width=6),

            # Estatisticas
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader([
                        html.I(className="fas fa-info-circle me-2"),
                        "Estatisticas do Periodo"
                    ]),
                    dbc.CardBody(id='period-stats')
                ])
            ], width=6),
        ], className="mb-4"),

        # Comparativo de fundos
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-balance-scale me-2"),
                "Comparativo de Fundos (Base 100)"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Selecione fundos para comparar:"),
                        dcc.Dropdown(
                            id='compare-funds-dropdown',
                            multi=True,
                            placeholder="Selecione ate 5 fundos..."
                        )
                    ], width=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-chart-line me-1"), "Comparar"],
                            id='compare-btn',
                            color="primary",
                            className="mt-4"
                        )
                    ], width=4)
                ], className="mb-3"),
                dcc.Loading(
                    dcc.Graph(id='compare-chart', config={'displayModeBar': True}),
                    type="circle"
                )
            ])
        ]),

        # Intervalo de refresh
        dcc.Interval(id='financial-refresh', interval=60000, n_intervals=0)
    ])


def register_callbacks(app):
    """Registra callbacks dos graficos financeiros"""

    @app.callback(
        [Output('fund-dropdown', 'options'),
         Output('compare-funds-dropdown', 'options')],
        Input('financial-refresh', 'n_intervals')
    )
    def load_funds(_):
        """Carrega lista de fundos"""
        try:
            funds_df = financial_queries.get_funds()
            options = [
                {'label': f"{row['nome_curto'] or row['nome_fundo']} ({row['tipo_fundo']})",
                 'value': row['id_fundo']}
                for _, row in funds_df.iterrows()
            ]
            return options, options
        except Exception as e:
            print(f"Erro ao carregar fundos: {e}")
            return [], []

    @app.callback(
        [Output('date-range', 'start_date'),
         Output('date-range', 'end_date')],
        [Input('btn-1m', 'n_clicks'),
         Input('btn-3m', 'n_clicks'),
         Input('btn-6m', 'n_clicks'),
         Input('btn-1a', 'n_clicks'),
         Input('btn-ytd', 'n_clicks'),
         Input('btn-max', 'n_clicks')],
        prevent_initial_call=True
    )
    def set_date_preset(b1, b3, b6, b12, bytd, bmax):
        """Define datas com base no preset"""
        from dash import ctx
        today = datetime.now().date()

        if ctx.triggered_id == 'btn-1m':
            return today - timedelta(days=30), today
        elif ctx.triggered_id == 'btn-3m':
            return today - timedelta(days=90), today
        elif ctx.triggered_id == 'btn-6m':
            return today - timedelta(days=180), today
        elif ctx.triggered_id == 'btn-1a':
            return today - timedelta(days=365), today
        elif ctx.triggered_id == 'btn-ytd':
            return datetime(today.year, 1, 1).date(), today
        else:  # max
            return None, None

    @app.callback(
        [Output('nav-chart', 'figure'),
         Output('flow-chart', 'figure'),
         Output('period-stats', 'children')],
        [Input('fund-dropdown', 'value'),
         Input('date-range', 'start_date'),
         Input('date-range', 'end_date')]
    )
    def update_fund_charts(fund_id, start_date, end_date):
        """Atualiza graficos do fundo selecionado"""
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark', height=400)

        if not fund_id:
            empty_fig.add_annotation(
                text="Selecione um fundo",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            return empty_fig, empty_fig, html.P("Selecione um fundo", className="text-muted")

        try:
            # Buscar dados
            df = financial_queries.get_nav_history(fund_id, start_date, end_date)

            if df.empty:
                empty_fig.add_annotation(
                    text="Sem dados para o periodo",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return empty_fig, empty_fig, html.P("Sem dados", className="text-muted")

            # Grafico NAV
            nav_fig = make_subplots(specs=[[{"secondary_y": True}]])

            nav_fig.add_trace(
                go.Scatter(
                    x=df['data_pos'],
                    y=df['pl_fechamento'],
                    name='PL',
                    fill='tozeroy',
                    line=dict(color='#3498db', width=2)
                ),
                secondary_y=False
            )

            nav_fig.add_trace(
                go.Scatter(
                    x=df['data_pos'],
                    y=df['cota_fechamento'],
                    name='Cota',
                    line=dict(color='#2ecc71', width=2)
                ),
                secondary_y=True
            )

            nav_fig.update_layout(
                template='plotly_dark',
                height=400,
                hovermode='x unified',
                legend=dict(orientation='h', y=1.1)
            )
            nav_fig.update_yaxes(title_text="Patrimonio (R$)", secondary_y=False)
            nav_fig.update_yaxes(title_text="Cota", secondary_y=True)

            # Grafico de fluxo
            flow_fig = go.Figure()

            if 'valor_entrada' in df.columns and 'valor_saida' in df.columns:
                df_flow = df[
                    (df['valor_entrada'].notna() & (df['valor_entrada'] != 0)) |
                    (df['valor_saida'].notna() & (df['valor_saida'] != 0))
                ]

                if not df_flow.empty:
                    flow_fig.add_trace(go.Bar(
                        x=df_flow['data_pos'],
                        y=df_flow['valor_entrada'].fillna(0),
                        name='Entradas',
                        marker_color='#27ae60'
                    ))

                    flow_fig.add_trace(go.Bar(
                        x=df_flow['data_pos'],
                        y=-df_flow['valor_saida'].fillna(0),
                        name='Saidas',
                        marker_color='#e74c3c'
                    ))

            flow_fig.update_layout(
                template='plotly_dark',
                height=300,
                barmode='relative',
                hovermode='x unified'
            )

            # Estatisticas
            pl_inicial = df['pl_fechamento'].iloc[0]
            pl_final = df['pl_fechamento'].iloc[-1]
            cota_inicial = df['cota_fechamento'].iloc[0] if df['cota_fechamento'].iloc[0] else 1
            cota_final = df['cota_fechamento'].iloc[-1] if df['cota_fechamento'].iloc[-1] else 1

            var_pl = ((pl_final / pl_inicial) - 1) * 100 if pl_inicial else 0
            var_cota = ((cota_final / cota_inicial) - 1) * 100 if cota_inicial else 0

            total_entradas = df['valor_entrada'].sum() if 'valor_entrada' in df.columns else 0
            total_saidas = df['valor_saida'].sum() if 'valor_saida' in df.columns else 0

            stats = html.Div([
                dbc.Row([
                    dbc.Col([
                        html.H6("PL Inicial", className="text-muted"),
                        html.H4(f"R$ {pl_inicial:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    ], width=6),
                    dbc.Col([
                        html.H6("PL Final", className="text-muted"),
                        html.H4(f"R$ {pl_final:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Var. PL", className="text-muted"),
                        html.H4(
                            f"{var_pl:+.2f}%",
                            className="text-success" if var_pl >= 0 else "text-danger"
                        )
                    ], width=6),
                    dbc.Col([
                        html.H6("Var. Cota", className="text-muted"),
                        html.H4(
                            f"{var_cota:+.2f}%",
                            className="text-success" if var_cota >= 0 else "text-danger"
                        )
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Total Entradas", className="text-muted"),
                        html.H5(f"R$ {total_entradas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                className="text-success")
                    ], width=6),
                    dbc.Col([
                        html.H6("Total Saidas", className="text-muted"),
                        html.H5(f"R$ {total_saidas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                                className="text-danger")
                    ], width=6)
                ])
            ])

            return nav_fig, flow_fig, stats

        except Exception as e:
            empty_fig.add_annotation(
                text=f"Erro: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="red")
            )
            return empty_fig, empty_fig, dbc.Alert(f"Erro: {e}", color="danger")

    @app.callback(
        Output('compare-chart', 'figure'),
        [Input('compare-btn', 'n_clicks')],
        [State('compare-funds-dropdown', 'value'),
         State('date-range', 'start_date'),
         State('date-range', 'end_date')],
        prevent_initial_call=True
    )
    def update_comparison(_, fund_ids, start_date, end_date):
        """Atualiza grafico comparativo"""
        fig = go.Figure()
        fig.update_layout(template='plotly_dark', height=400)

        if not fund_ids or len(fund_ids) < 2:
            fig.add_annotation(
                text="Selecione pelo menos 2 fundos para comparar",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="gray")
            )
            return fig

        try:
            df = financial_queries.get_fund_comparison(fund_ids, start_date, end_date)

            if df.empty:
                fig.add_annotation(
                    text="Sem dados para comparacao",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False,
                    font=dict(size=16, color="gray")
                )
                return fig

            # Normalizar para base 100
            for fund_name in df['nome_curto'].unique():
                fund_data = df[df['nome_curto'] == fund_name].copy()
                if not fund_data.empty:
                    base_value = fund_data['pl_fechamento'].iloc[0]
                    if base_value and base_value > 0:
                        normalized = (fund_data['pl_fechamento'] / base_value) * 100

                        fig.add_trace(go.Scatter(
                            x=fund_data['data_pos'],
                            y=normalized,
                            mode='lines',
                            name=fund_name
                        ))

            fig.add_hline(y=100, line_dash="dash", line_color="gray", annotation_text="Base 100")

            fig.update_layout(
                yaxis_title="Performance (Base 100)",
                hovermode='x unified',
                legend=dict(orientation='h', y=1.1)
            )

            return fig

        except Exception as e:
            fig.add_annotation(
                text=f"Erro: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=14, color="red")
            )
            return fig
