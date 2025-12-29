"""
ER Diagram - Diagrama de Entidade-Relacionamento com Cytoscape
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto

from database import schema_introspector
from config import VISIBLE_SCHEMAS

# Carregar layouts extras do Cytoscape
cyto.load_extra_layouts()

# Cores por schema
SCHEMA_COLORS = {
    'cad': '#3498db',      # Azul
    'pos': '#2ecc71',      # Verde
    'aux': '#e74c3c',      # Vermelho
    'stage': '#9b59b6'     # Roxo
}


def layout():
    """Layout do diagrama ER"""
    return html.Div([
        html.H2([
            html.I(className="fas fa-project-diagram me-2"),
            "Entity-Relationship Diagram"
        ], className="mb-4"),

        # Controles
        dbc.Row([
            dbc.Col([
                dbc.Label("Layout:"),
                dcc.Dropdown(
                    id='er-layout-dropdown',
                    options=[
                        {'label': 'Cose (Force-Directed)', 'value': 'cose'},
                        {'label': 'Dagre (Hierarchical)', 'value': 'dagre'},
                        {'label': 'Breadthfirst', 'value': 'breadthfirst'},
                        {'label': 'Circle', 'value': 'circle'},
                        {'label': 'Grid', 'value': 'grid'},
                        {'label': 'Concentric', 'value': 'concentric'},
                    ],
                    value='cose',
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Schemas:"),
                dcc.Dropdown(
                    id='er-schema-filter',
                    options=[{'label': s.upper(), 'value': s} for s in VISIBLE_SCHEMAS],
                    value=VISIBLE_SCHEMAS,
                    multi=True
                )
            ], width=4),
            dbc.Col([
                dbc.Button(
                    [html.I(className="fas fa-sync me-1"), "Atualizar"],
                    id='er-refresh-btn',
                    color="primary",
                    className="mt-4"
                ),
                dbc.Button(
                    [html.I(className="fas fa-expand me-1"), "Fit"],
                    id='er-fit-btn',
                    color="secondary",
                    className="mt-4 ms-2"
                )
            ], width=5)
        ], className="mb-3"),

        # Legenda
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.Span([
                        html.Span(className="legend-dot", style={'backgroundColor': SCHEMA_COLORS['cad']}),
                        " cad (Cadastral)"
                    ], className="me-3"),
                    html.Span([
                        html.Span(className="legend-dot", style={'backgroundColor': SCHEMA_COLORS['pos']}),
                        " pos (Posicoes)"
                    ], className="me-3"),
                    html.Span([
                        html.Span(className="legend-dot", style={'backgroundColor': SCHEMA_COLORS['aux']}),
                        " aux (Auxiliar)"
                    ], className="me-3"),
                    html.Span([
                        html.Span(className="legend-dot", style={'backgroundColor': SCHEMA_COLORS['stage']}),
                        " stage (Staging)"
                    ]),
                ], className="er-legend mb-3")
            ])
        ]),

        # Cytoscape
        dbc.Card([
            dbc.CardBody([
                cyto.Cytoscape(
                    id='er-cytoscape',
                    layout={'name': 'cose', 'nodeRepulsion': 400000, 'idealEdgeLength': 100},
                    style={'width': '100%', 'height': '600px'},
                    elements=[],
                    stylesheet=_get_cytoscape_stylesheet(),
                    minZoom=0.3,
                    maxZoom=3
                )
            ])
        ]),

        # Info panel
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-info-circle me-2"),
                "Detalhes"
            ]),
            dbc.CardBody(id='er-node-info')
        ], className="mt-3")
    ])


def _get_cytoscape_stylesheet():
    """Retorna estilos do Cytoscape"""
    styles = [
        # Estilo geral dos nos
        {
            'selector': 'node',
            'style': {
                'label': 'data(label)',
                'text-valign': 'center',
                'text-halign': 'center',
                'font-size': '10px',
                'color': 'white',
                'text-outline-color': '#222',
                'text-outline-width': 1,
                'width': 80,
                'height': 40,
                'shape': 'round-rectangle',
                'border-width': 2,
                'border-color': '#fff'
            }
        },
        # Estilo das arestas
        {
            'selector': 'edge',
            'style': {
                'width': 2,
                'line-color': '#888',
                'target-arrow-color': '#888',
                'target-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(label)',
                'font-size': '8px',
                'color': '#aaa',
                'text-rotation': 'autorotate'
            }
        },
        # Hover
        {
            'selector': 'node:selected',
            'style': {
                'border-width': 4,
                'border-color': '#ffcc00'
            }
        }
    ]

    # Adicionar cores por schema
    for schema, color in SCHEMA_COLORS.items():
        styles.append({
            'selector': f'.schema-{schema}',
            'style': {
                'background-color': color
            }
        })

    return styles


def _generate_er_elements(schemas):
    """Gera elementos do diagrama ER"""
    elements = []

    # Buscar tabelas de cada schema
    all_tables = {}
    for schema in schemas:
        tables_df = schema_introspector.get_tables(schema)
        for _, row in tables_df.iterrows():
            table_name = row['table_name']
            full_name = f"{schema}.{table_name}"
            all_tables[full_name] = {
                'schema': schema,
                'name': table_name,
                'type': row['table_type']
            }

            # Adicionar no
            elements.append({
                'data': {
                    'id': full_name,
                    'label': table_name,
                    'schema': schema,
                    'full_name': full_name
                },
                'classes': f'schema-{schema}'
            })

    # Buscar foreign keys
    fks_df = schema_introspector.get_foreign_keys()

    for _, fk in fks_df.iterrows():
        source = f"{fk['source_schema']}.{fk['source_table']}"
        target = f"{fk['target_schema']}.{fk['target_table']}"

        # Verificar se ambos estao nos schemas filtrados
        if source in all_tables and target in all_tables:
            elements.append({
                'data': {
                    'id': f"{source}->{target}",
                    'source': source,
                    'target': target,
                    'label': fk['source_column']
                }
            })

    return elements


def register_callbacks(app):
    """Registra callbacks do ER diagram"""

    @app.callback(
        Output('er-cytoscape', 'elements'),
        [Input('er-refresh-btn', 'n_clicks'),
         Input('er-schema-filter', 'value')],
        prevent_initial_call=False
    )
    def update_er_diagram(_, schemas):
        """Atualiza elementos do diagrama"""
        if not schemas:
            return []
        try:
            return _generate_er_elements(schemas)
        except Exception as e:
            print(f"Erro ao gerar ER: {e}")
            return []

    @app.callback(
        Output('er-cytoscape', 'layout'),
        Input('er-layout-dropdown', 'value')
    )
    def update_layout(layout_name):
        """Atualiza layout do diagrama"""
        layouts = {
            'cose': {'name': 'cose', 'nodeRepulsion': 400000, 'idealEdgeLength': 100, 'animate': True},
            'dagre': {'name': 'dagre', 'rankDir': 'TB', 'animate': True},
            'breadthfirst': {'name': 'breadthfirst', 'directed': True, 'animate': True},
            'circle': {'name': 'circle', 'animate': True},
            'grid': {'name': 'grid', 'animate': True},
            'concentric': {'name': 'concentric', 'animate': True}
        }
        return layouts.get(layout_name, layouts['cose'])

    @app.callback(
        Output('er-cytoscape', 'zoom'),
        Input('er-fit-btn', 'n_clicks'),
        prevent_initial_call=True
    )
    def fit_diagram(_):
        """Ajusta zoom para caber tudo"""
        return 1

    @app.callback(
        Output('er-node-info', 'children'),
        Input('er-cytoscape', 'tapNodeData')
    )
    def show_node_info(data):
        """Mostra info do no clicado"""
        if not data:
            return html.P("Clique em uma tabela para ver detalhes", className="text-muted")

        schema = data.get('schema')
        table = data.get('label')

        if not schema or not table:
            return html.P("Dados nao disponiveis", className="text-muted")

        try:
            cols_df = schema_introspector.get_columns(schema, table)
            pk_cols = schema_introspector.get_primary_keys(schema, table)
            row_count = schema_introspector.get_table_row_count(schema, table)

            col_items = []
            for _, col in cols_df.iterrows():
                is_pk = col['column_name'] in pk_cols
                col_items.append(
                    html.Li([
                        html.I(className="fas fa-key text-warning me-1") if is_pk else None,
                        html.Strong(col['column_name']),
                        f" ({col['full_type']})"
                    ])
                )

            return html.Div([
                html.H5([
                    html.I(className="fas fa-table me-2"),
                    f"{schema}.{table}"
                ]),
                html.P([
                    html.I(className="fas fa-list-ol me-1"),
                    f" {row_count:,} registros | ",
                    html.I(className="fas fa-columns me-1"),
                    f" {len(cols_df)} colunas"
                ], className="text-muted"),
                html.Ul(col_items[:10], className="small"),
                html.P(f"... +{len(cols_df) - 10} colunas", className="text-muted small") if len(cols_df) > 10 else None,
                dbc.Button(
                    [html.I(className="fas fa-external-link-alt me-1"), "Abrir detalhes"],
                    href=f"/table?schema={schema}&table={table}",
                    color="primary",
                    size="sm"
                )
            ])

        except Exception as e:
            return dbc.Alert(f"Erro: {e}", color="danger")
