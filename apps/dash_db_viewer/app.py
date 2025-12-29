"""
PostgreSQL Database Viewer - Dashboard com Plotly Dash
Entry point principal da aplicacao
"""

import sys
import os

# Adiciona o diretorio ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dash import Dash, html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from config import APP_CONFIG
from database import db_manager, schema_introspector, financial_queries

# Importar paginas
from pages.home import layout as home_layout, register_callbacks as home_callbacks
from pages.schema_explorer import layout as schema_layout, register_callbacks as schema_callbacks
from pages.table_details import layout as table_layout, register_callbacks as table_callbacks
from pages.er_diagram import layout as er_layout, register_callbacks as er_callbacks
from pages.financial_charts import layout as financial_layout, register_callbacks as financial_callbacks

# Importar componentes
from components.sidebar import create_sidebar, register_callbacks as sidebar_callbacks

# =============================================================================
# INICIALIZACAO DO APP
# =============================================================================

app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.FONT_AWESOME
    ],
    suppress_callback_exceptions=True,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ]
)

app.title = APP_CONFIG['title']
server = app.server

# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

app.layout = dbc.Container([
    # Store para dados compartilhados
    dcc.Store(id='selected-schema', data='cad'),
    dcc.Store(id='selected-table', data=None),
    dcc.Location(id='url', refresh=False),

    # Header
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.I(className="fas fa-database me-2"),
                    dbc.NavbarBrand("PostgreSQL Database Viewer", className="ms-2")
                ], width="auto"),
            ], align="center", className="g-0"),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Home", href="/", id="nav-home")),
                dbc.NavItem(dbc.NavLink("Schemas", href="/schema", id="nav-schema")),
                dbc.NavItem(dbc.NavLink("ER Diagram", href="/er-diagram", id="nav-er")),
                dbc.NavItem(dbc.NavLink("Financeiro", href="/financial", id="nav-financial")),
            ], className="ms-auto", navbar=True)
        ], fluid=True),
        color="primary",
        dark=True,
        className="mb-3"
    ),

    # Conteudo principal
    dbc.Row([
        # Sidebar
        dbc.Col(
            create_sidebar(),
            width=2,
            className="sidebar-col"
        ),
        # Main content
        dbc.Col(
            html.Div(id='page-content', className="main-content"),
            width=10
        )
    ], className="g-0"),

], fluid=True, className="app-container")

# =============================================================================
# CALLBACK DE NAVEGACAO
# =============================================================================

@callback(
    Output('page-content', 'children'),
    Input('url', 'pathname'),
    Input('selected-schema', 'data'),
    Input('selected-table', 'data')
)
def display_page(pathname, schema, table):
    """Renderiza a pagina baseado na URL"""
    if pathname == '/schema':
        return schema_layout()
    elif pathname == '/table' and schema and table:
        return table_layout(schema, table)
    elif pathname == '/er-diagram':
        return er_layout()
    elif pathname == '/financial':
        return financial_layout()
    else:
        return home_layout()


@callback(
    [Output('nav-home', 'active'),
     Output('nav-schema', 'active'),
     Output('nav-er', 'active'),
     Output('nav-financial', 'active')],
    Input('url', 'pathname')
)
def update_nav_active(pathname):
    """Atualiza estado ativo do nav"""
    return [
        pathname == '/' or pathname is None,
        pathname == '/schema' or pathname == '/table',
        pathname == '/er-diagram',
        pathname == '/financial'
    ]


# =============================================================================
# REGISTRAR CALLBACKS DAS PAGINAS
# =============================================================================

sidebar_callbacks(app)
home_callbacks(app)
schema_callbacks(app)
table_callbacks(app)
er_callbacks(app)
financial_callbacks(app)

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    # Testar conexao
    print("Testando conexao com o banco...")
    if db_manager.test_connection():
        print("Conexao OK!")
        print(f"\nIniciando servidor em http://{APP_CONFIG['host']}:{APP_CONFIG['port']}")
        app.run(
            debug=APP_CONFIG['debug'],
            host=APP_CONFIG['host'],
            port=APP_CONFIG['port']
        )
    else:
        print("ERRO: Nao foi possivel conectar ao banco de dados.")
        print("Verifique as configuracoes em config.py ou no arquivo .env")
        sys.exit(1)
