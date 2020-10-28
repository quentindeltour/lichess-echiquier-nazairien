from datetime import date, timedelta, datetime
import os
import re
import dateutil.parser
import locale
from dateutil.relativedelta import relativedelta
from io import StringIO

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import dash_table

import pandas as pd
import plotly.express as px
import ndjson

from utils import create_lichess_session, get, Header, update_club_informations, update_global_tournament_ranking, update_players_list, update_tournament_list, update_tables_club_puzzle, filter_list_between_strings
from utils_s3 import create_s3_object, read_s3_csv_file, get_list_s3_objects

from controls import GAME_MODE

locale.setlocale(locale.LC_TIME, 'fr_FR')

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

#mettre fonction pour scraper infos du club UNE FOIS !  
club = 'echiquier-nazairien'


client = create_lichess_session()
name, description, president, nbmembers, ville = update_club_informations(club)
liste_joueurs, players_options, player_value = update_players_list(club)
tournament_options, tournament_value = update_tournament_list(club)
data_table_général, columns_table_général = update_global_tournament_ranking(club)

#OPTIONS
game_mode_options =[
    {"label": str(value), "value": str(key)} for key, value in GAME_MODE.items()
]

app = dash.Dash(
    __name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}]
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
                                    style={'width': '20%', 'float': 'center','display': 'inline-block'},
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
                            value='bullet',
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
    df_table = df[['username', 'perfs.{}.games'.format(game_mode), 'perfs.{}.rating'.format(game_mode), 'perfs.{}.prog'.format(game_mode)]]
    data_table = df_table.sort_values('perfs.{}.rating'.format(game_mode), ascending=False).to_dict('records')
    columns_table=[
        {"name": 'Joueur', "id": 'username'}, {'name':'Nombre de parties', 'id':'perfs.{}.games'.format(game_mode)},
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
            className="sub_pagetwo",
        ),
    ],
    className="pagetwo",
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
    df_table = df[[2, 3, 4]].sort_values(by=4, ascending=False)
    df_table.columns = ['Nom du Joueur', 'Classement Elo', 'Nombre de Points']
    df_table['Classement'] = range(1,len(df_table)+1,1)
    data_table = df_table.to_dict('records')
    columns_table=[{'name': col, 'id': col} for col in ['Classement','Nom du Joueur', 'Classement Elo', 'Nombre de Points']]
    return data_table,columns_table

#General Tournament Page

tournament_general_layout = html.Div(
    [
        html.Div(Header(app)),
        html.Br(),
        html.Div(
            [
                html.Div(
                    html.H4("Classement Général des Tournois", className='subtitle'

                    ),
                ),
                html.Div( 
                    [
                        dash_table.DataTable(
                            id='table_global_tournoi',
                            data=data_table_général,
                            columns=columns_table_général,
                            sort_action='native',
                            page_action="native",
                            page_current= 0,
                            page_size=30,
                        )
                    ]
                )
            ],
            className="sub_page",
            style={"margin-bottom": "25px"},
        ),
    ],
    className='page'
)

# Puzzle Challenge Page
today = date.today()

date_puzzle_options = [
    {'label': dateutil.parser.parse(re.sub('-puzzle.csv', '', file)).strftime("%A %d %B %Y"), 'value':re.sub('-puzzle.csv', '', file)} for file in get_list_s3_objects()
]

date_puzzle_value_first = '2020-10-23'
date_puzzle_value_last = '{}-{}-{}'.format(today.year, today.month, today.day)

def make_puzzle_layout():
    return html.Div(
            [
                html.Div(Header(app)),
                html.Br(),
                html.Div(
                    [
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.H6("Date de début :"),
                                        dcc.Dropdown(
                                            id='date_debut',
                                            value=date_puzzle_value_first,
                                            clearable=False
                                        )
                                    ],
                                    className='six columns'
                                ),
                                html.Div(
                                    [
                                        html.H6("Date de fin :"),
                                        dcc.Dropdown(
                                            id='date_fin',
                                            value=date_puzzle_value_last,
                                            clearable=False
                                        )
                                    ],
                                    className='six columns'
                                ),
                            ],
                            className='row'
                        ),
                        html.Br(),
                        html.Button('Mettre à jour les données', id='update-val', n_clicks=0),
                        html.Div(id='phrase-update'),
                        html.Br(),
                        html.H4("Classement du challenge puzzle", className='subtitle'),
                        html.Div( 
                            [
                                dash_table.DataTable(
                                    id='table-puzzle-challenge',
                                    sort_action='native',
                                    filter_action="native",
                                    page_action="native",
                                    page_current= 0,
                                    page_size=25,
                                )
                            ],
                        )
                    ],
                    className='sub_page'
                )
            ],
            className='page'
        )

@app.callback(
    Output('date_fin', 'options'),
    Input('date_debut', 'value')
)
def update_enddate_options(date_debut):
    liste_date = [re.sub('-puzzle.csv', '', file) for file in get_list_s3_objects()]
    possible_date = list(set([date for date in liste_date if date >= date_debut]))
    return [{'label': dateutil.parser.parse(date).strftime("%A %d %B %Y"), 'value':date} for date in possible_date]

@app.callback(
    Output('date_debut', 'options'),
    Input('date_fin', 'value')
)
def update_debutdate_options(date_fin):
    liste_date = [re.sub('-puzzle.csv', '', file) for file in get_list_s3_objects()]
    possible_date = list(set([date for date in liste_date if date <= date_fin]))
    return [{'label': dateutil.parser.parse(date).strftime("%A %d %B %Y"), 'value':date} for date in possible_date]

@app.callback(
    Output('phrase-update', 'children'),
    [Input('update-val', 'n_clicks')],
)
def update_table_s3(n_clicks):
    s3 = create_s3_object()
    df = update_tables_club_puzzle(club)
    now = datetime.today()
    key = '{}-{}-{}-puzzle.csv'.format(now.year, now.month, now.day)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer)
    s3.Object('lichess-app-assets',key).put(Body=csv_buffer.getvalue())
    return 'Les données ont été enregistrées le {} à {} heures {}.'.format(
        dateutil.parser.parse(str(now)).strftime("%A %d %B %Y"),  
        now.hour, now.minute
    )


@app.callback(
    [Output('table-puzzle-challenge', 'data'),
    Output('table-puzzle-challenge', 'columns')],
    [Input('date_debut', 'value'), Input('date_fin', 'value')]
)
def update_puzzle_challenge(date_debut, date_fin):
    df_first = read_s3_csv_file('{}-puzzle.csv'.format(date_debut))
    df_last = read_s3_csv_file('{}-puzzle.csv'.format(date_fin))
    df_first[['perfs.puzzle.games', 'perfs.puzzle.rating']] = df_first[['perfs.puzzle.games', 'perfs.puzzle.rating']].astype(float)
    df_first.set_index('username', inplace=True)
    df_last.set_index('username', inplace=True)
    df_last[['perfs.puzzle.games', 'perfs.puzzle.rating']] = df_last[['perfs.puzzle.games', 'perfs.puzzle.rating']].astype(float)
    df_table = df_last[['perfs.puzzle.games', 'perfs.puzzle.rating']].subtract(df_first[['perfs.puzzle.games', 'perfs.puzzle.rating']])
    df_table['Joueur'] = df_table.index
    df_table.rename(columns={"perfs.puzzle.games": "Puzzles effectués", "perfs.puzzle.rating":"Diff Elo"}, inplace=True)
    liste_df=[read_s3_csv_file(file) for file in filter_list_between_strings(date_debut, date_fin, get_list_s3_objects())]
    rating = pd.concat(liste_df)
    gb = rating.groupby('username')
    rating_max = pd.DataFrame(gb['perfs.puzzle.rating'].max())
    df_table = df_table.merge(rating_max.rename(columns={'perfs.puzzle.rating':'Elo Max'}),left_index=True, right_index=True)
    df_table = df_table.merge(pd.DataFrame(df_last['perfs.puzzle.games']).rename(columns={'perfs.puzzle.games':'Total Puzzles'}),left_index=True, right_index=True)
    df_table = df_table.merge(pd.DataFrame(df_last['perfs.puzzle.rating']).rename(columns={'perfs.puzzle.rating':'Elo Final'}),left_index=True, right_index=True)
    df_table.sort_values('Elo Final', ascending=False, inplace=True)
    data_table = df_table.to_dict('records')
    columns_table=[{'name': col, 'id': col} for col in ["Joueur",'Total Puzzles',"Puzzles effectués",'Elo Final','Elo Max',"Diff Elo"]]
    return data_table, columns_table


# Update page
@app.callback(Output("page-content", "children"), [Input("url", "pathname")])
def display_page(pathname):
    if pathname == "/dash-echiquier-nazairien/individual-results":
        return individual_layout
    elif pathname == "/dash-echiquier-nazairien/puzzle-results":
        return make_puzzle_layout()
    elif pathname == "/dash-echiquier-nazairien/tournament-results":
        return tournament_layout
    elif pathname == "/dash-echiquier-nazairien/tournament-general-results":
        return tournament_general_layout    
    elif pathname == "/dash-echiquier-nazairien/full-view":
        return (
            overview_layout,
            individual_layout,
            tournament_layout,
            tournament_general_layout,
            make_puzzle_layout(),
        )
    else:
        return overview_layout


if __name__ == "__main__":
    app.run_server(debug=True)