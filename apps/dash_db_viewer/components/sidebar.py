"""
Sidebar - Menu lateral com arvore de schemas e tabelas
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from database import schema_introspector, VISIBLE_SCHEMAS


def create_sidebar():
    """Cria o componente sidebar"""
    return html.Div([
        html.H5("Schemas", className="sidebar-title"),
        html.Hr(),
        html.Div(id='schema-tree', className="schema-tree"),
        dcc.Interval(id='refresh-interval', interval=60000, n_intervals=0)  # Refresh a cada minuto
    ], className="sidebar")


def register_callbacks(app):
    """Registra callbacks do sidebar"""

    @app.callback(
        Output('schema-tree', 'children'),
        Input('refresh-interval', 'n_intervals')
    )
    def update_schema_tree(_):
        """Atualiza a arvore de schemas"""
        try:
            schemas_df = schema_introspector.get_schemas()

            tree_items = []
            for _, row in schemas_df.iterrows():
                schema_name = row['schema_name']
                table_count = row['table_count']

                # Buscar tabelas do schema
                tables_df = schema_introspector.get_tables(schema_name)

                # Criar accordion para cada schema
                table_links = []
                for _, tbl in tables_df.iterrows():
                    table_links.append(
                        dbc.ListGroupItem(
                            [
                                html.I(className="fas fa-table me-2 text-muted"),
                                tbl['table_name']
                            ],
                            href=f"/table?schema={schema_name}&table={tbl['table_name']}",
                            action=True,
                            className="table-link"
                        )
                    )

                schema_item = dbc.Accordion([
                    dbc.AccordionItem(
                        dbc.ListGroup(table_links, flush=True),
                        title=html.Span([
                            html.I(className="fas fa-folder me-2"),
                            f"{schema_name} ({table_count})"
                        ]),
                        item_id=schema_name
                    )
                ], id=f"accordion-{schema_name}", start_collapsed=True, className="mb-2")

                tree_items.append(schema_item)

            return tree_items

        except Exception as e:
            return html.Div([
                html.I(className="fas fa-exclamation-triangle me-2 text-warning"),
                f"Erro: {str(e)}"
            ], className="text-danger")
