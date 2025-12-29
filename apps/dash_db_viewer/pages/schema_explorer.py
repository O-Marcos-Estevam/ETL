"""
Schema Explorer - Explorador de schemas e tabelas
"""

from dash import html, dcc, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc

from database import schema_introspector
from config import VISIBLE_SCHEMAS


def layout():
    """Layout do schema explorer"""
    return html.Div([
        html.H2([
            html.I(className="fas fa-database me-2"),
            "Schema Explorer"
        ], className="mb-4"),

        # Seletor de schema
        dbc.Row([
            dbc.Col([
                dbc.Label("Schema:"),
                dcc.Dropdown(
                    id='schema-dropdown',
                    options=[{'label': s, 'value': s} for s in VISIBLE_SCHEMAS],
                    value='cad',
                    clearable=False
                )
            ], width=4)
        ], className="mb-4"),

        # Tabela de tabelas
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-list me-2"),
                html.Span(id='tables-header')
            ]),
            dbc.CardBody([
                html.Div(id='tables-list')
            ])
        ])
    ])


def register_callbacks(app):
    """Registra callbacks do schema explorer"""

    @app.callback(
        [Output('tables-header', 'children'),
         Output('tables-list', 'children')],
        Input('schema-dropdown', 'value')
    )
    def update_tables_list(schema):
        """Atualiza lista de tabelas do schema"""
        if not schema:
            return "Selecione um schema", html.Div()

        try:
            tables_df = schema_introspector.get_tables(schema)

            # Adicionar contagem de registros
            row_counts = []
            for _, row in tables_df.iterrows():
                count = schema_introspector.get_table_row_count(schema, row['table_name'])
                row_counts.append(f"{count:,}" if count > 0 else "~0")
            tables_df['rows'] = row_counts

            # Criar cards para cada tabela
            table_cards = []
            for _, row in tables_df.iterrows():
                table_name = row['table_name']
                table_type = row['table_type']
                size = row['size']
                rows = row['rows']

                # Buscar colunas
                cols_df = schema_introspector.get_columns(schema, table_name)
                pk_cols = schema_introspector.get_primary_keys(schema, table_name)

                # Preview das colunas
                col_preview = []
                for _, col in cols_df.head(6).iterrows():
                    is_pk = col['column_name'] in pk_cols
                    col_preview.append(
                        html.Span([
                            html.I(className="fas fa-key text-warning me-1") if is_pk else None,
                            f"{col['column_name']} ",
                            html.Small(f"({col['full_type']})", className="text-muted")
                        ], className="d-block")
                    )

                if len(cols_df) > 6:
                    col_preview.append(
                        html.Small(f"... +{len(cols_df) - 6} colunas", className="text-muted")
                    )

                icon = "fa-table" if table_type == "BASE TABLE" else "fa-eye"

                table_cards.append(
                    dbc.Col(
                        dbc.Card([
                            dbc.CardHeader([
                                html.I(className=f"fas {icon} me-2"),
                                html.Strong(table_name),
                                dbc.Badge(
                                    "VIEW" if table_type == "VIEW" else "TABLE",
                                    color="info" if table_type == "VIEW" else "primary",
                                    className="ms-2"
                                )
                            ]),
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Small([
                                            html.I(className="fas fa-hdd me-1"),
                                            size
                                        ], className="text-muted d-block"),
                                        html.Small([
                                            html.I(className="fas fa-list-ol me-1"),
                                            f"{rows} registros"
                                        ], className="text-muted d-block"),
                                        html.Small([
                                            html.I(className="fas fa-columns me-1"),
                                            f"{len(cols_df)} colunas"
                                        ], className="text-muted d-block"),
                                    ], width=5),
                                    dbc.Col([
                                        html.Div(col_preview, className="small")
                                    ], width=7)
                                ]),
                                dbc.Button(
                                    [html.I(className="fas fa-search me-1"), "Detalhes"],
                                    href=f"/table?schema={schema}&table={table_name}",
                                    color="primary",
                                    size="sm",
                                    className="mt-2"
                                )
                            ])
                        ], className="mb-3 h-100"),
                        width=6
                    )
                )

            return (
                f"Tabelas em {schema} ({len(tables_df)} encontradas)",
                dbc.Row(table_cards)
            )

        except Exception as e:
            return "Erro", dbc.Alert(f"Erro: {e}", color="danger")
