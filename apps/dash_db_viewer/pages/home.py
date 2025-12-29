"""
Home Page - Overview do banco de dados
"""

from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc

from database import schema_introspector, financial_queries, db_manager
from config import DB_CONFIG


def layout():
    """Layout da pagina home"""
    return html.Div([
        html.H2([
            html.I(className="fas fa-home me-2"),
            "Database Overview"
        ], className="mb-4"),

        # Connection info card
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-plug me-2"),
                "Conexao"
            ]),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.P([html.Strong("Host: "), DB_CONFIG['host']], className="mb-1"),
                        html.P([html.Strong("Database: "), DB_CONFIG['database']], className="mb-1"),
                        html.P([html.Strong("User: "), DB_CONFIG['user']], className="mb-1"),
                    ], width=6),
                    dbc.Col([
                        html.Div(id='connection-status')
                    ], width=6)
                ])
            ])
        ], className="mb-4"),

        # Stats cards
        html.Div(id='stats-cards', className="mb-4"),

        # Schema summary
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-database me-2"),
                "Schemas"
            ]),
            dbc.CardBody(id='schema-summary')
        ], className="mb-4"),

        dcc.Interval(id='home-refresh', interval=30000, n_intervals=0)
    ])


def register_callbacks(app):
    """Registra callbacks da home"""

    @app.callback(
        Output('connection-status', 'children'),
        Input('home-refresh', 'n_intervals')
    )
    def update_connection_status(_):
        """Verifica status da conexao"""
        if db_manager.test_connection():
            return dbc.Alert([
                html.I(className="fas fa-check-circle me-2"),
                "Conectado"
            ], color="success", className="mb-0")
        else:
            return dbc.Alert([
                html.I(className="fas fa-times-circle me-2"),
                "Desconectado"
            ], color="danger", className="mb-0")

    @app.callback(
        Output('stats-cards', 'children'),
        Input('home-refresh', 'n_intervals')
    )
    def update_stats(_):
        """Atualiza cards de estatisticas"""
        try:
            stats = financial_queries.get_database_stats()

            # Formatar PL
            pl_formatted = f"R$ {stats['pl_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

            return dbc.Row([
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H3(stats['total_fundos'], className="text-primary mb-0"),
                            html.P("Fundos Ativos", className="text-muted mb-0")
                        ])
                    ], className="stat-card"),
                    width=3
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H3(stats['total_cotistas'], className="text-info mb-0"),
                            html.P("Cotistas Ativos", className="text-muted mb-0")
                        ])
                    ], className="stat-card"),
                    width=3
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H5(pl_formatted, className="text-success mb-0"),
                            html.P("PL Total (Ultima Data)", className="text-muted mb-0")
                        ])
                    ], className="stat-card"),
                    width=3
                ),
                dbc.Col(
                    dbc.Card([
                        dbc.CardBody([
                            html.H6([
                                str(stats['data_inicial']) if stats['data_inicial'] else 'N/A',
                                html.Br(),
                                "ate ",
                                str(stats['data_final']) if stats['data_final'] else 'N/A'
                            ], className="text-warning mb-0"),
                            html.P("Periodo de Dados", className="text-muted mb-0")
                        ])
                    ], className="stat-card"),
                    width=3
                ),
            ])
        except Exception as e:
            return dbc.Alert(f"Erro ao carregar estatisticas: {e}", color="danger")

    @app.callback(
        Output('schema-summary', 'children'),
        Input('home-refresh', 'n_intervals')
    )
    def update_schema_summary(_):
        """Atualiza resumo de schemas"""
        try:
            schemas_df = schema_introspector.get_schemas()

            cards = []
            for _, row in schemas_df.iterrows():
                tables_df = schema_introspector.get_tables(row['schema_name'])

                table_list = html.Ul([
                    html.Li(f"{t['table_name']} ({t['size']})")
                    for _, t in tables_df.head(5).iterrows()
                ], className="small mb-0")

                if len(tables_df) > 5:
                    table_list = html.Div([
                        table_list,
                        html.P(f"... e mais {len(tables_df) - 5} tabelas", className="text-muted small")
                    ])

                cards.append(
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className="fas fa-folder me-2"),
                                html.Strong(row['schema_name'].upper())
                            ]),
                            dbc.CardBody([
                                html.H4(f"{row['table_count']} tabelas", className="mb-2"),
                                table_list
                            ])
                        ], className="h-100"),
                        width=3
                    )
                )

            return dbc.Row(cards)
        except Exception as e:
            return html.Div(f"Erro: {e}", className="text-danger")
