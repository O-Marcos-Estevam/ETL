"""
Table Details - Detalhes de uma tabela especifica
"""

from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from urllib.parse import parse_qs

from database import schema_introspector


def layout(schema=None, table=None):
    """Layout dos detalhes da tabela"""
    return html.Div([
        # Hidden stores para schema e table
        dcc.Store(id='current-schema', data=schema),
        dcc.Store(id='current-table', data=table),
        dcc.Location(id='table-url', refresh=False),

        html.Div(id='table-details-content')
    ])


def register_callbacks(app):
    """Registra callbacks do table details"""

    @app.callback(
        [Output('current-schema', 'data'),
         Output('current-table', 'data')],
        Input('table-url', 'search')
    )
    def parse_url_params(search):
        """Parse query params da URL"""
        if search:
            params = parse_qs(search.lstrip('?'))
            schema = params.get('schema', [None])[0]
            table = params.get('table', [None])[0]
            return schema, table
        return None, None

    @app.callback(
        Output('table-details-content', 'children'),
        [Input('current-schema', 'data'),
         Input('current-table', 'data')]
    )
    def update_table_details(schema, table):
        """Renderiza detalhes da tabela"""
        if not schema or not table:
            return dbc.Alert(
                "Selecione uma tabela no menu lateral ou no Schema Explorer.",
                color="info"
            )

        try:
            # Buscar dados
            cols_df = schema_introspector.get_columns(schema, table)
            pk_cols = schema_introspector.get_primary_keys(schema, table)
            indexes_df = schema_introspector.get_indexes(schema, table)
            row_count = schema_introspector.get_table_row_count(schema, table)

            # Sample data
            try:
                sample_df = schema_introspector.get_sample_data(schema, table, 10)
            except:
                sample_df = None

            return html.Div([
                # Header
                html.H2([
                    html.I(className="fas fa-table me-2"),
                    f"{schema}.{table}"
                ], className="mb-2"),

                # Breadcrumb
                dbc.Breadcrumb(items=[
                    {"label": "Schemas", "href": "/schema"},
                    {"label": schema, "href": f"/schema?s={schema}"},
                    {"label": table, "active": True}
                ], className="mb-4"),

                # Stats row
                dbc.Row([
                    dbc.Col(
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(f"{row_count:,}", className="mb-0"),
                                html.Small("Registros (estimativa)", className="text-muted")
                            ])
                        ]),
                        width=3
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(len(cols_df), className="mb-0"),
                                html.Small("Colunas", className="text-muted")
                            ])
                        ]),
                        width=3
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(len(pk_cols), className="mb-0"),
                                html.Small("Primary Keys", className="text-muted")
                            ])
                        ]),
                        width=3
                    ),
                    dbc.Col(
                        dbc.Card([
                            dbc.CardBody([
                                html.H4(len(indexes_df), className="mb-0"),
                                html.Small("Indices", className="text-muted")
                            ])
                        ]),
                        width=3
                    ),
                ], className="mb-4"),

                # Tabs
                dbc.Tabs([
                    # Tab: Colunas
                    dbc.Tab([
                        html.Div(
                            _create_columns_table(cols_df, pk_cols),
                            className="mt-3"
                        )
                    ], label="Colunas", tab_id="tab-columns"),

                    # Tab: Indices
                    dbc.Tab([
                        html.Div(
                            _create_indexes_table(indexes_df),
                            className="mt-3"
                        )
                    ], label="Indices", tab_id="tab-indexes"),

                    # Tab: Sample Data
                    dbc.Tab([
                        html.Div(
                            _create_sample_table(sample_df) if sample_df is not None else
                            dbc.Alert("Nao foi possivel carregar amostra de dados", color="warning"),
                            className="mt-3"
                        )
                    ], label="Amostra de Dados", tab_id="tab-sample"),

                    # Tab: SQL
                    dbc.Tab([
                        html.Div(
                            _create_sql_preview(schema, table, cols_df, pk_cols),
                            className="mt-3"
                        )
                    ], label="SQL", tab_id="tab-sql"),
                ], id="table-tabs", active_tab="tab-columns")
            ])

        except Exception as e:
            return dbc.Alert(f"Erro ao carregar tabela: {e}", color="danger")


def _create_columns_table(cols_df, pk_cols):
    """Cria tabela de colunas"""
    # Adicionar indicador de PK
    cols_df = cols_df.copy()
    cols_df['is_pk'] = cols_df['column_name'].isin(pk_cols)

    # Formatar nullable
    cols_df['nullable'] = cols_df['is_nullable'].apply(
        lambda x: 'Sim' if x == 'YES' else 'Nao'
    )

    # Formatar default
    cols_df['default'] = cols_df['column_default'].apply(
        lambda x: str(x)[:50] if x else '-'
    )

    return dash_table.DataTable(
        data=cols_df[['column_name', 'full_type', 'nullable', 'default', 'is_pk']].to_dict('records'),
        columns=[
            {'name': 'Coluna', 'id': 'column_name'},
            {'name': 'Tipo', 'id': 'full_type'},
            {'name': 'Nullable', 'id': 'nullable'},
            {'name': 'Default', 'id': 'default'},
            {'name': 'PK', 'id': 'is_pk'}
        ],
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#303030',
            'fontWeight': 'bold',
            'border': '1px solid #444'
        },
        style_cell={
            'backgroundColor': '#222',
            'color': 'white',
            'border': '1px solid #444',
            'textAlign': 'left',
            'padding': '10px'
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{is_pk} = true'},
                'backgroundColor': '#3d5a80',
                'fontWeight': 'bold'
            },
            {
                'if': {'filter_query': '{nullable} = Nao'},
                'color': '#ffc107'
            }
        ],
        filter_action='native',
        sort_action='native',
        page_size=20
    )


def _create_indexes_table(indexes_df):
    """Cria tabela de indices"""
    if indexes_df.empty:
        return dbc.Alert("Nenhum indice encontrado", color="info")

    return dash_table.DataTable(
        data=indexes_df.to_dict('records'),
        columns=[
            {'name': 'Nome', 'id': 'indexname'},
            {'name': 'Definicao', 'id': 'indexdef'}
        ],
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#303030',
            'fontWeight': 'bold',
            'border': '1px solid #444'
        },
        style_cell={
            'backgroundColor': '#222',
            'color': 'white',
            'border': '1px solid #444',
            'textAlign': 'left',
            'padding': '10px',
            'whiteSpace': 'normal',
            'height': 'auto'
        },
        style_cell_conditional=[
            {'if': {'column_id': 'indexdef'}, 'maxWidth': '500px'}
        ]
    )


def _create_sample_table(sample_df):
    """Cria tabela com amostra de dados"""
    if sample_df.empty:
        return dbc.Alert("Tabela vazia", color="info")

    # Limitar largura das colunas
    for col in sample_df.columns:
        sample_df[col] = sample_df[col].astype(str).str[:100]

    return dash_table.DataTable(
        data=sample_df.to_dict('records'),
        columns=[{'name': c, 'id': c} for c in sample_df.columns],
        style_table={'overflowX': 'auto'},
        style_header={
            'backgroundColor': '#303030',
            'fontWeight': 'bold',
            'border': '1px solid #444'
        },
        style_cell={
            'backgroundColor': '#222',
            'color': 'white',
            'border': '1px solid #444',
            'textAlign': 'left',
            'padding': '8px',
            'maxWidth': '200px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis'
        },
        page_size=10,
        tooltip_data=[
            {col: {'value': str(val), 'type': 'text'} for col, val in row.items()}
            for row in sample_df.to_dict('records')
        ],
        tooltip_duration=None
    )


def _create_sql_preview(schema, table, cols_df, pk_cols):
    """Cria preview de comandos SQL uteis"""
    columns = cols_df['column_name'].tolist()

    # SELECT
    col_list = ',\n    '.join(columns[:10])
    select_sql = f"SELECT\n    {col_list}"
    if len(columns) > 10:
        select_sql += f"\n    -- ... +{len(columns) - 10} colunas"
    select_sql += f"\nFROM {schema}.{table}\nLIMIT 100;"

    # INSERT template
    insert_cols = ', '.join(columns[:8])
    insert_sql = f"INSERT INTO {schema}.{table} (\n    {insert_cols}"
    if len(columns) > 8:
        insert_sql += f"\n    -- ... +{len(columns) - 8} colunas"
    insert_sql += "\n) VALUES (\n    -- valores aqui\n);"

    # COUNT
    count_sql = f"SELECT COUNT(*) FROM {schema}.{table};"

    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("SELECT"),
                    dbc.CardBody([
                        html.Pre(select_sql, className="sql-code")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("INSERT (template)"),
                    dbc.CardBody([
                        html.Pre(insert_sql, className="sql-code")
                    ])
                ])
            ], width=6)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("COUNT"),
                    dbc.CardBody([
                        html.Pre(count_sql, className="sql-code")
                    ])
                ])
            ], width=4)
        ])
    ])
