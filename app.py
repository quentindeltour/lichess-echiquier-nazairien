from datetime import timedelta, datetime
import re
import dateutil.parser
import locale
from dateutil.relativedelta import relativedelta
import os
import base64

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table
import dash_bootstrap_components as dbc

import pandas as pd
import plotly.express as px
import ndjson

from utils import create_lichess_session, get, Header, update_club_informations, update_players_list, update_tournament_list, update_team_arena_list
#from utils_s3 import create_s3_object, read_s3_csv_file, get_list_s3_objects

from controls import GAME_MODE, TOURNOIS, CATEGORIES_DROPDOWN, FAMILLES, CATEGORIES, ID_NOM, TEAMS_ID

locale.setlocale(locale.LC_TIME, 'fr_FR')
pd.options.mode.chained_assignment = None

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#mettre fonction pour scraper infos du club UNE FOIS !  
club = 'echiquier-nazairien'


client = create_lichess_session()
name, description, president, nbmembers, ville = update_club_informations(club)
liste_joueurs, players_options, player_value = update_players_list(club)
tournament_options, tournament_value = update_tournament_list(club)

team_arena_options, team_arena_value = update_team_arena_list(club)

#data_table_général, columns_table_général = update_global_tournament_ranking(club)

#OPTIONS
game_mode_options =[
    {"label": str(value), "value": str(key)} for key, value in GAME_MODE.items()
]

tournois_options = [
    {"label": str(value), "value": str(key)} for key, value in TOURNOIS.items()
]

categories_options = [
    {"label": str(value), "value": str(key)} if key not in ['Elo', 'Age'] else {"label": str(value), "value": str(key), 'disabled':True} for key, value in CATEGORIES_DROPDOWN.items()
]

app = dash.Dash(
    __name__, 
    title='Echiquier Nazairien',
    update_title='En cours de chargement...',
    meta_tags=[{"name": "viewport", "content": "width=device-width"},],
    external_stylesheets=[dbc.themes.FLATLY]
)

app.config['suppress_callback_exceptions'] = True

server = app.server

app.layout = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-content")]
)

overview_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Div(
            [
                #Description club
                html.Div(
                    [
                        html.Div(
                            [
                                html.H5("Description du club"),
                                html.Br([]),
                                html.P(
                                    str(description),
                                    #style={"color": "#ffffff"},
                                    className="row",
                                )
                            ],
                            className="big-product",
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.P("Nom du Club :"), html.H6(name)
                                    ],
                                    id="statut",
                                    style={'width': '26%', 'float': 'left','display': 'inline-block'},
                                    className="product ",
                                ),
                                html.Div(
                                    [
                                        html.P("Président : "), html.H6(president), 
                                    ],
                                    id="cadence",
                                    style={'width': '23%', 'float': 'center','display': 'inline-block'},
                                    className="product ",
                                ),
                                html.Div(
                                    [
                                        html.P("Nombre de joueurs : "), html.H6(nbmembers), 
                                    ],
                                    id="nb_joueurs_tournoi",
                                    style={'width': '24%', 'float': 'right','display': 'inline-block'},
                                    className="product ",
                                ),
                                html.Div(
                                    [
                                        html.P("Ville :"), html.H6(ville)
                                    ],
                                    id="nb_parties_tournoi",
                                    style={'width': '24%', 'float': 'right','display': 'inline-block'},
                                    className="product ",
                                ),
                            ],
                            id="info-container-tournoi",
                            className="row container-display twelve columns",
                        ),
                    ],
                    #className="row",

                ),
                html.Br(),
                #Description métriques clubs
                html.Div(
                    [
                        html.Div(
                            [
                            html.H4("Meilleurs joueurs par mode de jeu : "),
                            ],
                        ),
                        html.H6("Choisis un mode de jeu :", className="subtitle"),
                        dcc.Dropdown(
                            id='game_mode_club',
                            options=game_mode_options,
                            value='blitz',
                            clearable=False
                        ),
                        html.Div(
                            [
                                html.Div(
                                    [
                                        dash_table.DataTable(
                                            id='table_game_mode',
                                            data=[],
                                            sort_action='native',
                                            filter_action="native",
                                            page_action="native",
                                            page_current= 0,
                                            page_size=15,
                                            style_data_conditional=[
                                                {
                                                    'if': {'row_index': 'odd'},
                                                    'backgroundColor': 'rgb(248, 248, 248)'
                                                }
                                            ],
                                            style_header={
                                                'backgroundColor': 'rgb(230, 230, 230)',
                                                'fontWeight': 'bold'
                                            },
                                        )
                                    ]
                                ),
                            ],
                        ),
                    ]
                )
            ],
            className="sub_page",
        )
    ],
    className="page",
)

@app.callback(
[
    Output('table_game_mode', 'data'), Output('table_game_mode', 'columns'),
],
[
    Input('game_mode_club', 'value'),
],
)
def update_tables_club(game_mode):
    rep = get("https://lichess.org/api/team/{}/users".format(str(club)))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df_table = df[['username', 'id', 'perfs.{}.games'.format(game_mode), 'perfs.{}.rating'.format(game_mode), 'perfs.{}.prog'.format(game_mode)]]
    df_table['Nom'] = df_table['id'].apply(lambda x:ID_NOM.get(str(x), "inconnu"))
    data_table = df_table.sort_values('perfs.{}.rating'.format(game_mode), ascending=False).to_dict('records')
    columns_table=[
        {"name": 'Joueur', "id": 'username'},{"name": 'Nom', "id": 'Nom'}, {'name':'Nombre de parties', 'id':'perfs.{}.games'.format(game_mode)},
        {'name':'Classement Elo', 'id':'perfs.{}.rating'.format(game_mode)}, {'name':'Progression', 'id':'perfs.{}.prog'.format(game_mode)}
    ]
    return data_table,columns_table


# Indivudal Page  : 

individual_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Br(),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H6("Choisis un joueur :"),
                                dcc.Dropdown(
                                id='joueurs',
                                options=players_options,
                                value=player_value,
                                clearable=False
                                ),
                            ],
                            className='one-half column'
                        ),
                        html.A(
                            html.Button("Voir le joueur", id="player-lichess-button"),
                            id='player_lichess_club',
                        )
                    ],
                    className='row'
                ),
                html.Br(),
                dcc.Graph(id='indicator-graphic'),
            ],
            className="sub_page",
        ),
    ],
    className="page",
)

@app.callback(
    [Output('player_lichess_club', 'href')],
    [Input('joueurs', 'value')],
)
def update_link(joueurs):
    return ["https://lichess.org/@/{}".format(joueurs)]


@app.callback(
    Output('indicator-graphic', 'figure'),
    [Input('joueurs', 'value'),
    ]
)
def update_graph(joueurs):
    #Création DF_USER
    df_indiv = pd.DataFrame(client.users.get_rating_history(str(joueurs)))
    df_user = df_indiv.merge(pd.DataFrame(df_indiv.points.array), right_index=True, left_index=True) 
    df_user.drop('points', axis=1, inplace=True)
    #Melt
    meelt = pd.melt(df_user, id_vars='name', value_vars=range(len(df_user.columns)-1))
    meelt.dropna(inplace=True)
    meelt.drop('variable', axis=1, inplace=True)
    meelt.set_index('name', inplace=True)
    df_meelt = pd.DataFrame(meelt.value.array, index=meelt.index)
    df_meelt.reset_index(inplace=True)
    df_meelt.month = df_meelt.month +1
    df_plot = df_meelt[['name', 'rating']].merge(pd.DataFrame(pd.to_datetime(df_meelt[['year', 'month', 'day']], errors='coerce'), columns=['date']), left_index=True, right_index=True)
    df_plot.rename(columns={'name' : 'Mode de jeu'}, inplace=True)
    fig = px.line(df_plot, x="date", y="rating", color='Mode de jeu')

    fig.update_xaxes(
        title='Temps',
        rangeslider_visible=True,
        rangeselector=dict(
            buttons=list([
                dict(count=7, label="1w", step="day", stepmode="backward"),
                dict(count=14, label="2w", step="day", stepmode="backward"),
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(label='all', step="all")
            ]),
            buttondefaults=dict(label='YTD')
        )
    )
    now = datetime.today()
    six_month = now - relativedelta(month=6)
    initial_range = [
    str(now.year) + '-01-01', str(now).split()[0]
    ]

    fig['layout']['xaxis'].update(range=initial_range)
    fig.update_yaxes(title='Classement Elo')
    fig.update_layout(
        title={
            'text': "Evolution du Classement Elo de {}".format(joueurs),
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        }
    )
    return fig


# Tournament page : 

tournament_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Div(
            [
                html.Div(
                    [
                        html.Div(
                            [
                                html.H6("Choisis un tournoi :"),
                                dcc.Dropdown(
                                    id='tournoi',
                                    options=tournament_options,
                                    value=tournament_value,
                                    clearable=False
                                ),
                            ],
                            style={'width': '48%', 'float': 'left','display': 'inline-block', "margin-bottom": "25px"},
                            className="one-half column",
                        ),
                        html.A(
                            html.Button("Télécharger les parties", id="tournament-games-lichess-button"),
                            id='tournament_games_lichess_club',
                        )
                    ],
                    className="row",
                    style={"margin-bottom": "25px"},
                ),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.Div(
                                                    [
                                                        html.P("Statut :"), html.H6(id="statut_tournoi")
                                                    ],
                                                    id="statut",
                                                    style={'width': '20%', 'float': 'left','display': 'inline-block'},
                                                    className="product ",
                                                ),
                                                html.Div(
                                                    [
                                                        html.P("Cadence : "), html.H6(id="time_limit_tournoi"), 
                                                    ],
                                                    id="cadence",
                                                    style={'width': '25%', 'float': 'center','display': 'inline-block'},
                                                    className="product ",
                                                ),
                                                html.Div(
                                                    [
                                                        html.P("Nombre de joueurs : "), html.H6(id="players_tournoi"), 
                                                    ],
                                                    id="nb_joueurs_tournoi",
                                                    style={'width': '25%', 'float': 'right','display': 'inline-block'},
                                                    className="product ",
                                                ),
                                                html.Div(
                                                    [
                                                        html.P("Nombre de parties :"), html.H6(id="rounds_tournoi")
                                                    ],
                                                    id="nb_parties_tournoi",
                                                    style={'width': '25%', 'float': 'right','display': 'inline-block'},
                                                    className="product ",
                                                ),
                                            ],
                                            id="info-container-tournoi",
                                            className="row container-display twelve columns",
                                        ),
                                        html.Div(
                                            [
                                                html.P("Date du tournoi : "), html.H6(id="date_tournoi"), 
                                            ],
                                                id="date-tournament",
                                                style={'width': '48%','float':'left','display': 'inline-block'},                            
                                                className="product",
                                        ),
                                    ],
                                    className= 'row twelve columns'
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            [
                                                html.H4("Classement du tournoi", className='subtitle'),
                                            ],
                                            style={'float': 'left','display': 'inline-block', "margin-bottom": "25px"},
                                        ),
                                        html.Div(
                                            [
                                                dash_table.DataTable(
                                                    id='table_tournoi',
                                                    data=[],
                                                    sort_action='native',
                                                    page_action="native",
                                                    page_current= 0,
                                                    page_size=20,
                                                    style_data_conditional=[
                                                        {
                                                            'if': {'row_index': 'odd'},
                                                            'backgroundColor': 'rgb(248, 248, 248)'
                                                        }
                                                    ],
                                                    style_header={
                                                        'backgroundColor': 'rgb(230, 230, 230)',
                                                        'fontWeight': 'bold'
                                                    },
                                                )
                                            ]
                                        ),
                                    ],
                                    id="right-column-tournoi",
                                    className="twelve columns",
                                    style={"margin-bottom": "25px"},
                                ),
                            ],
                            className="row flex-display",
                        ),
                    ],
                ),
            ],
            className="sub_page",
        ),
    ],
    className="page",
)

@app.callback(
    [Output('tournament_games_lichess_club', 'href')],
    [Input('tournoi', 'value')],
)
def update_link_tournoi(id_tournoi):
    return ["https://lichess.org/api/swiss/{}/games".format(id_tournoi)]


@app.callback(
    [Output('date_tournoi', 'children'), 
    Output('time_limit_tournoi', 'children'), 
    Output('rounds_tournoi', 'children'), 
    Output('players_tournoi', 'children'), 
    Output('statut_tournoi', 'children')],
    [Input('tournoi', 'value')],
)
def update_tournament_informations(tourn_id):
    rep = get('https://lichess.org/api/team/{}/swiss'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df_info = df[df.id == tourn_id]
    date = (dateutil.parser.parse(df_info['startsAt'].array[0]) +timedelta(hours=2)).strftime("%A %d %B %Y %H:%M:%S")
    time_limit = "{} min + {}s/coup".format(int(df_info['clock.limit'].array[0]/60), str(df_info['clock.increment'].array[0]))
    nb_rounds = df_info.nbRounds.array[0]
    nb_players = df_info.nbPlayers.array[0]
    if df_info.status.array[0] == 'finished':
        statut = 'Terminé'
    elif df_info.status.array[0] == 'created':
        statut = 'A venir'
    else:
        statut = 'En cours'
    return date, time_limit, nb_rounds, nb_players, statut


@app.callback(
    [Output('table_tournoi', 'data'), Output('table_tournoi', 'columns'),],
    [Input('tournoi', 'value'),],
)
def update_tournament_results(tourn_id):
    rep = get("https://lichess.org/swiss/{}.trf".format(str(tourn_id)))
    lines = [line for line in rep.text.splitlines()]
    list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
    df = pd.DataFrame(list_df)
    df[4]=df[4].astype(float)
    df_table = df[[2, 3, 4]].sort_values(by=4, ascending=False)
    df_table.columns = ['Pseudo', 'Classement Elo', 'Nombre de Points']
    df_table['Nom du Joueur'] = df_table['Pseudo'].apply(lambda x:ID_NOM.get(str(x), "inconnu"))
    df_table['Classement'] = range(1,len(df_table)+1,1)
    data_table = df_table.to_dict('records')
    columns_table=[{'name': col, 'id': col} for col in ['Classement','Pseudo','Nom du Joueur', 'Classement Elo', 'Nombre de Points']]
    return data_table,columns_table

#General Tournament Page

dropdown = dbc.DropdownMenu(
    [   
        dbc.DropdownMenuItem("Classement par catégories Elo", header=True) ,
        dbc.DropdownMenuItem("Plus de 1800", id='1800+'),
        dbc.DropdownMenuItem("Entre 1500 et 1800", id='1500-1800'),
        dbc.DropdownMenuItem("Entre 1300 et 1500", id='1300-1500'),
        dbc.DropdownMenuItem("Entre 1100 et 1300", id='1100-1300'),
        dbc.DropdownMenuItem("Moins de 1100", id='1100-'),
        dbc.DropdownMenuItem(divider=True),
        dbc.DropdownMenuItem("Classement par catégories d'âge", header=True),
        dbc.DropdownMenuItem("Veteran", id='Veteran'),
        dbc.DropdownMenuItem("Senior +", id='Senior+'),
        dbc.DropdownMenuItem("Senior", id='Senior'),
        dbc.DropdownMenuItem("Cadet/Junior", id='Cadet'),            
        dbc.DropdownMenuItem("Minime", id='Minime'),
        dbc.DropdownMenuItem("Benjamin", id='Benjamin'),            
        dbc.DropdownMenuItem("Pupille", id='Pupille'),
        dbc.DropdownMenuItem("Poussin", id='Poussin'),            
        dbc.DropdownMenuItem("Petit Poussin", id='Petit Poussin'),
    ],
    label="Choix des catégories",
)


tournament_general_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Br(),
        html.Div(
            [
                dcc.Dropdown(
                    id='type-tournoi',
                    options=tournois_options,
                    value='2021',
                    clearable=False
                ),
                html.Br(),
                html.Div(id='classement-tournois-catégories'),
                html.Div(
                    [
                        dcc.Tabs(
                            [
                                dcc.Tab(
                                    [
                                        dash_table.DataTable(
                                            id='table_global_tournoi',
                                            sort_action='native',
                                            page_action="native",
                                            page_current= 0,
                                            page_size=30,
                                            style_data_conditional=[
                                                {
                                                    'if': {'row_index': 'odd'},
                                                    'backgroundColor': 'rgb(248, 248, 248)'
                                                }
                                            ],
                                            style_header={
                                                'backgroundColor': 'rgb(230, 230, 230)',
                                                'fontWeight': 'bold'
                                            },
                                        ), 
                                    ],
                                    label="Classement Général",
                                    #tab_id="tab-1",
                                    #tabClassName="ml-auto"
                                ), 
                                dcc.Tab(
                                    [
                                        dash_table.DataTable(
                                            id='table_global_familles',
                                            sort_action='native',
                                            page_action="native",
                                            page_current= 0,
                                            page_size=30,
                                            style_data_conditional=[
                                                {
                                                    'if': {'row_index': 'odd'},
                                                    'backgroundColor': 'rgb(248, 248, 248)'
                                                }
                                            ],
                                            style_header={
                                                'backgroundColor': 'rgb(230, 230, 230)',
                                                'fontWeight': 'bold'
                                            },
                                        ), 
                                    ],
                                    label="Classement des familles",
                                    #tab_id='tab-2',
                                    #tabClassName="ml-auto"
                                ),
                                    
                                dcc.Tab(
                                    [
                                        dcc.Dropdown(
                                            id='categorie',
                                            options=categories_options,
                                            value='Senior',
                                            clearable=False
                                        ),
                                        dash_table.DataTable(
                                            id='table_global_categories',
                                            sort_action='native',
                                            page_action="native",
                                            page_current= 0,
                                            page_size=30,
                                            style_data_conditional=[
                                                {
                                                    'if': {'row_index': 'odd'},
                                                    'backgroundColor': 'rgb(248, 248, 248)'
                                                }
                                            ],
                                            style_header={
                                                'backgroundColor': 'rgb(230, 230, 230)',
                                                'fontWeight': 'bold'
                                            },
                                        ), 
                                    ],
                                    label="Classement par catégories",
                                    #tab_id='tab-3',
                                    #tabClassName="ml-auto"
                                )
                            ], 
                            id='tab-classement',
                            #active_tab='tab-1'
                        )
                    ],
                    className='table-custom'
                ),
            ],
            className="sub_page",
            style={"margin-bottom": "25px"},
        ),
    ],
    className='page'
)

@app.callback(
    [Output('table_global_tournoi', 'data'), Output('table_global_tournoi', 'columns'),
     Output('table_global_familles', 'data'), Output('table_global_familles', 'columns'),
     Output('table_global_categories', 'data'), Output('table_global_categories', 'columns'),
     ],
    [Input('type-tournoi', 'value'), Input('categorie', 'value')]
)
def update_classement_general(type_tournoi, categorie):
    rep = get('https://lichess.org/api/team/{}/swiss'.format(club))
    items = rep.json(cls=ndjson.Decoder)
    df = pd.json_normalize(items)
    df_list = []
    if type_tournoi == 'ete':
        for id_tourn in df[df.startsAt < "2020-08-31"].id:
            rep = get("https://lichess.org/swiss/{}.trf".format(str(id_tourn)))
            lines = [line for line in rep.text.splitlines()]
            list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
            df_list.append(pd.DataFrame(list_df))
    elif type_tournoi=='confinement2':
        for id_tourn in df[(df.startsAt >= "2020-10-28")&(df.startsAt < "2020-12-31") & (df.status=='finished')].id:
            rep = get("https://lichess.org/swiss/{}.trf".format(str(id_tourn)))
            lines = [line for line in rep.text.splitlines()]
            list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
            df_list.append(pd.DataFrame(list_df))
    elif type_tournoi=='2021':
        for id_tourn in df[(df.startsAt >= "2021-01-01") & (df.status=='finished')].id:
            rep = get("https://lichess.org/swiss/{}.trf".format(str(id_tourn)))
            lines = [line for line in rep.text.splitlines()]
            list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
            df_list.append(pd.DataFrame(list_df))
    else:    
        for id_tourn in df.id:
            rep = get("https://lichess.org/swiss/{}.trf".format(str(id_tourn)))
            lines = [line for line in rep.text.splitlines()]
            list_df = [re.split('[ ]{2,}', string_) for string_ in lines if string_.startswith('001')]
            df_list.append(pd.DataFrame(list_df))
    df_final = pd.concat(df_list)
    df_final[4] = df_final[4].astype(float)
    gb = df_final.groupby(2)
    df_table = pd.DataFrame(gb[4].sum()).merge(pd.DataFrame(gb[4].count()), left_index=True, right_index=True)
    df_table['Pseudo'] = df_table.index
    df_table['Nom du Joueur'] = df_table['Pseudo'].apply(lambda x:ID_NOM.get(str(x), "inconnu"))
    df_table.rename(columns={'4_x':'Score total', '4_y':'Nombre de tournois joués'}, inplace=True)
    df_table.sort_values('Score total', ascending=False, inplace=True)
    df_table['Classement Général'] = range(1,len(df_table)+1,1)

    dic_resultats = {key: df_table.loc[df_table.Pseudo.isin(value)]['Score total'].sum() for key, value in FAMILLES.items()}
    df_famille = pd.DataFrame.from_dict(dic_resultats, orient='index', columns=['Score total'])
    df_famille['Nom'] = df_famille.index
    df_famille['Membres'] = [','.join(liste) for liste in FAMILLES.values()]
    df_famille['Classement'] = range(1,len(df_famille)+1,1)

    final_categories = {
    '1800+':[x for x in df_table.index if x in CATEGORIES.get('1800+')],
    '1500-1800':[x for x in df_table.index if x in CATEGORIES.get('1500-1800')],
    '1300-1500':[x for x in df_table.index if x in CATEGORIES.get('1300-1500')],
    '1100-1300':[x for x in df_table.index if x in CATEGORIES.get('1100-1300')],
    '1100-':[x for x in df_table.index if x in CATEGORIES.get('1100-')],
    'Veteran':[x for x in df_table.index if x in CATEGORIES.get('Veteran')],
    'Senior+':[x for x in df_table.index if x in CATEGORIES.get('Senior+')],
    'Senior':[x for x in df_table.index if x in CATEGORIES.get('Senior')],
    'Cadet/Junior':[x for x in df_table.index if x in CATEGORIES.get('Cadet/Junior')],
    'Minime':[x for x in df_table.index if x in CATEGORIES.get('Minime')],
    'Benjamin':[x for x in df_table.index if x in CATEGORIES.get('Benjamin')],
    'Pupille':[x for x in df_table.index if x in CATEGORIES.get('Pupille')],
    'Poussin':[x for x in df_table.index if x in CATEGORIES.get('Poussin')],
    'Petit Poussin':[x for x in df_table.index if x in CATEGORIES.get('Petit Poussin')],
    }

    df_categorie = df_table.loc[final_categories.get(categorie)]

    columns_table=[{'name': col, 'id': col} for col in ['Classement Général', 'Pseudo','Nom du Joueur','Nombre de tournois joués','Score total' ]]
    columns_table_famille=[{'name': col, 'id': col} for col in ['Classement', 'Nom','Score total','Membres']]
    columns_table_categorie = [{'name': col, 'id': col} for col in ['Classement Général', 'Pseudo','Nom du Joueur','Nombre de tournois joués','Score total' ]]

    return df_table.to_dict('records'), columns_table, df_famille.sort_values('Score total', ascending=False).to_dict('records'), columns_table_famille, df_categorie.to_dict('records'), columns_table_categorie


image_directory =  os.getcwd() + '/assets/'
logo_pdl = image_directory + 'logo_pdl.png'
encoded_logo_pdl = base64.b64encode(open(logo_pdl, 'rb').read())

team_tournament_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Br(),
        html.Div(
            [
                html.Div(
                [
                    html.Img(
                        src='data:image/png;base64,{}'.format(encoded_logo_pdl.decode()),
                        className='logo-interclub'
                    ),
                    html.H6('(Logo Vincent VERHILLE)')
                ],
                className='three columns',
                ),
                html.Div([
                    html.H6('Choisis un tournoi :'),
                    dcc.Dropdown(
                        id = 'dropdown-team-arena',
                        options = team_arena_options,
                        value=team_arena_value,
                        clearable=False,
                        )
                        ],className='five columns'
                ),
                html.A(
                html.Button("Télécharger les parties", id="tournament-games-lichess-button"),
                id='tournament_team_href',
                ),
            ],
            className="row",
        ),
        html.Hr(),
        html.Div(id='classement-team'),
        html.Div(id="classement-top-10"),
        html.Div(id='classement-indiv')
    ],
    className='page'
)


@app.callback(
    Output('classement-team', 'children'), Output('classement-top-10', 'children'),Output('classement-indiv', 'children'),
    Input('dropdown-team-arena', 'value')
)
def update_team_arena_result(tournoi):
    rep = get('https://lichess.org/api/tournament/{}'.format(tournoi))
    df = pd.json_normalize(rep.json().get('teamStanding'))
    columns = ['Classement', 'Club', 'Score']
    df.rename(columns={'rank':'Classement', 'score':'Score'}, inplace=True)
    df['Club'] = df['id'].apply(lambda x:TEAMS_ID.get(str(x), "non renseigné"))
    div_general = html.Div(
        [
            html.H4('Classement général de cette étape : '),
            dash_table.DataTable(
                id='table_tournoi',
                data=df[columns].to_dict('records'),
                columns=[{'name': col, 'id': col} for col in columns],
                sort_action='native',
                page_action="native",
                page_current= 0,
                page_size=20,
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        'if': {
                            'filter_query': '{Club} contains "Echiquier Nazairien"',
                        },
                        'backgroundColor': 'yellow',
                        'color': 'black'
                    },

                ],
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
            )
        ], 
        className='centered-table'
    )

    top_ten = pd.json_normalize(rep.json().get('standing').get('players'))
    top_ten.rename(columns={'name':'Pseudo', 'sheet.total':'Score', 'rank':'Classement'}, inplace=True)
    top_ten['Club'] = top_ten['team'].apply(lambda x:TEAMS_ID.get(str(x), "non renseigné"))
    columns = ['Classement', 'Pseudo','Club','Score']
    div_top_ten = html.Div(
        [
            html.H4('Classement individuel de cette étape : '),
            dash_table.DataTable(
                id='table_tournoi',
                data=top_ten[columns].to_dict('records'),
                columns=[{'name': col, 'id': col} for col in columns],
                sort_action='native',
                page_action="native",
                page_current= 0,
                page_size=20,
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    },
                    {
                        'if': {
                            'filter_query': '{Club} contains "Echiquier Nazairien"',
                        },
                        'backgroundColor': 'yellow',
                        'color': 'black'
                    },
                ],
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
            )
        ], 
        className='centered-table'
    )



    index = df[df.id == club].index[0]
    df2 = pd.json_normalize(df.loc[index, 'players'])
    df2['Nom'] = df2['user.id'].apply(lambda x:ID_NOM.get(str(x), "inconnu"))
    df2.rename(columns={'user.name':'Pseudo', 'score':'Score'}, inplace=True)
    columns = ['Score', 'Pseudo','Nom']
    div_st_nazaire = html.Div(
        [
            html.H4('Meilleurs nazairiens de cette étape : '),
            dash_table.DataTable(
                id='table_tournoi',
                data=df2[columns].to_dict('records'),
                columns=[{'name': col, 'id': col} for col in columns],
                sort_action='native',
                page_action="native",
                page_current= 0,
                page_size=20,
                style_data_conditional=[
                    {
                        'if': {'row_index': 'odd'},
                        'backgroundColor': 'rgb(248, 248, 248)'
                    }
                ],
                style_header={
                    'backgroundColor': 'rgb(230, 230, 230)',
                    'fontWeight': 'bold'
                },
            )
        ], 
        className='centered-table'
    )
    return div_general, div_top_ten, div_st_nazaire

@app.callback(
    [Output('tournament_team_href', 'href')],
    [Input('dropdown-team-arena', 'value')],
)
def update_link_tournoi(id_tournoi):
    return ["https://lichess.org/api/arena/{}/games".format(id_tournoi)]

test_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Br(),
        html.Div(
            [
                dcc.Tabs(
                    [
                        dcc.Tab(
                            [
                                html.Div(
                                    [
                                        html.Br(),
                                        html.Iframe(src="https://lichess.org/tv/frame?theme=brown&bg=dark", width="400px", height= "444px")
                                    ],
                                ),
                            ], label="Meilleur partie Live"
                        ),
                        dcc.Tab(
                            [
                                html.Div(
                                    [
                                        html.Br(),
                                        html.Iframe(src="https://lichess.org/training/frame?theme=brown&bg=dark", width="400px", height= "444px")
                                    ],
                                ),
                            ], label="Pratique en tactique !"
                        ),
                        dcc.Tab(
                            [
                                html.Div(
                                    [
                                        html.Br(),
                                        html.Iframe(src="https://lichess.org/embed/JwB4U3zj#33?theme=auto&bg=auto", width=600, height=397)
                                    ],
                                ),
                            ], label = "Masterpiece de Quentin Deschamps (c'est faux)"
                        ),
                    ])
        ])
    ],
    className='page'
)



# Update page
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/echiquier-nazairien/individual-results":
        return individual_layout
    elif pathname == "/echiquier-nazairien/tournament-results":
        return tournament_layout
    elif pathname == "/echiquier-nazairien/tournament-swiss-results":
        return tournament_general_layout
    elif pathname == "/echiquier-nazairien/tournament-team-results":
        return team_tournament_layout
    elif pathname == "/echiquier-nazairien/test":
        return test_layout
    elif pathname == "/echiquier-nazairien/full-view":
        return (
            overview_layout,
            individual_layout,
            tournament_layout,
            tournament_general_layout,
            team_tournament_layout
        )
    else:
        return overview_layout


if __name__ == "__main__":
    app.run_server(debug=True)