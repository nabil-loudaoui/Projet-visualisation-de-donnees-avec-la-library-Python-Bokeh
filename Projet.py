import pandas as pd
import numpy as np
import json
from pandas import DataFrame
from bokeh.plotting import figure, show
from bokeh.palettes import Set1
from bokeh.models import HoverTool, ColumnDataSource, Legend, Range1d, Column, Div,Row, LegendItem, PanTool, WheelZoomTool, Tabs, Panel, Div
from bokeh.tile_providers import  get_provider,OSM
from bokeh.io import curdoc
from bokeh.layouts import row,gridplot
from bokeh.models import  Spinner
from bokeh.layouts import layout


#############################################################
# theme 
curdoc().theme = 'dark_minimal'

#fonction pour transformer le fichier json
def coor_wgs84_to_web_mercator(lon, lat):
    k = 6378137
    x = lon * (k * np.pi/180.0)
    y = np.log(np.tan((90 + lat) * np.pi/360.0)) * k
    return (x,y)

def analyse_data(data):
    # Construction d'un dataframe : une colonne denomination, une colonne trafic, une colonne coordonnéees
    axe = []
    coordsx = []  # Pour chaque zone, liste des coordonnées x de la polyligne
    coordsy = []  # Pour chaque zone, liste des coordonnées y de la polyligne

    for trajet in data:
        if "axe" in trajet["fields"].keys():
            axe.append(trajet["fields"]["axe"])
            coords = trajet["fields"]["geo_shape"]["coordinates"]
            c_x = []
            c_y = []
            for c in coords[0]:
                x, y = coor_wgs84_to_web_mercator(c[0], c[1])
                c_x.append(x)
                c_y.append(y)
            coordsx.append(c_x)
            coordsy.append(c_y)

    df = DataFrame({'axe': axe, 'x':coordsx, 'y': coordsy})
    return df

def plot_bar_chart(df, variable, x_label, y_label):
    p = figure(x_range=df['code_departement'].astype(str), height=250, title=f" Proportion {variable}")
    p.xaxis.axis_label = x_label
    p.yaxis.axis_label = y_label
    p.vbar(x='code_departement', top=variable, width=0.9, source=df)
    p.xgrid.grid_line_color = None
    p.y_range.start = 0
    hover_tool1 = HoverTool(tooltips=[('code de departement', '@code_departement'),
                                      ('Proportion', '@{d}'.format(d=variable))])
    p.add_tools(hover_tool1)
    return p



###################################################
# importation Partie 1 : 
data_trafic_ferri = pd.read_csv("trafic_ferries.csv", sep=";").sort_values(by=["Date"])
# Conversion de la colonne "Date" en datetime
data_trafic_ferri["Date"] = pd.to_datetime(data_trafic_ferri["Date"], format="%Y-%m")
data_trafic_ferri["Year"] = data_trafic_ferri["Date"].dt.year
# Agrégation des données par mois et par année
data_trafic_ferri = data_trafic_ferri.groupby([data_trafic_ferri["Year"], data_trafic_ferri["Date"].dt.month_name().str.slice(stop=3)], sort=False)["Nombre_passagers"].sum().reset_index()
data_trafic_ferri.columns = ["Year", "Month", "Nombre_passagers"]

# importation Partie 2 :

data_compteur=pd.read_csv("compteurs-cyclistespietons.csv",sep=';')
data_compteur=data_compteur.drop(['photo', 'pdf','Geo Shape', 'gml_id','type','brigade'],axis=1).drop(10)
data_compteur["ident_num"] = data_compteur["ident"].str.extract(r"(\d+)").astype(int)

data_compteur["Geo Point"]=data_compteur["Geo Point"].str.split(",")

trafic=data_compteur.drop(['Geo Point', 'ident', 'nom', 'observation', 'rive', 'subdivision','trafic_total', 'millesime'],axis=1)
trafic=trafic.sort_values(by="ident_num",ascending=True)
trafic["ident_num"] = trafic["ident_num"].astype(str)

# Coordonnees : 
data_compteur["x"]=[float(x[1]) for x in data_compteur["Geo Point"]]
data_compteur["y"]=[float(y[0]) for y in data_compteur["Geo Point"]]
data_compteur["x"],data_compteur["y"]=coor_wgs84_to_web_mercator(data_compteur["x"],data_compteur["y"])


# Importation Partie 3 : 

data_tronc = open("troncons-ferroviaires-regionaux-de-la-region-bretagne.json","r",encoding='utf-8')
dico = json.load(data_tronc)
data_tronc_ferrov = analyse_data(dico)

# Source des données
source1=ColumnDataSource(trafic)
source2=ColumnDataSource(data_compteur)
source3 = ColumnDataSource(data_tronc_ferrov)

#####################################################
# graphique 1 :

colors = Set1[6]
p = figure(x_range=list(data_trafic_ferri["Month"].unique()), y_range=(0, data_trafic_ferri["Nombre_passagers"].max()+5000), tools=[PanTool(), WheelZoomTool()], title="Nombre de passagers pour chaque année de 2017 à 2022")
legend_items = []
colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown']
source6 = ColumnDataSource(data=data_trafic_ferri)
for i, year in enumerate(range(2017, 2023)):
    legend_items.append(
        LegendItem(label=str(year),
                   renderers=[p.line(
                       data_trafic_ferri.loc[data_trafic_ferri["Year"] == year, "Month"],
                       data_trafic_ferri.loc[data_trafic_ferri["Year"] == year, "Nombre_passagers"],
                       line_width=2,
                       color=colors[i]
                   )
                   ]
                  )
    )
circle = p.circle(x='Month', y='Nombre_passagers', source=source6, alpha=1, size=5)
p.add_layout(Legend(items=legend_items, location='top_left', click_policy='hide'))
# Créer l'outil de survol
hover_tool = HoverTool(tooltips=[('Année', '@{Year}'), ('Nombre de passagers', '@{Nombre_passagers}')], 
                       renderers=[circle])

# Ajouter l'outil de survol à la figure
p.add_tools(hover_tool)

div = Div(
    text="""
          <p>Sélectionnez la taille du cercle des points :</p>
          """,
    width=200,
    height=30,
)

spinner = Spinner(
    title="Circle size",
    low=0, 
    high=60,  
    step=2,  
    value= circle.glyph.size,  
    width=200,  
    )
spinner.js_link("value", circle.glyph, "size")

p = layout(
    [
        [div, spinner],
        [p],
    ]
)

#show(layout)

####################################################
# graphique 2 :

hover_tool = HoverTool(tooltips=[( 'Nom  ', '@nom'),
                                 ('Trafic de vélo','@trafic_velo'),
                                 ('Trafic de pieton','@trafic_pieton')])
p2 = figure(x_axis_type="mercator", y_axis_type="mercator", active_scroll="wheel_zoom", title="carte")
tile_provider = get_provider(OSM)
p2.add_tile(tile_provider)
p2.circle(x="x",y="y",source=source2,size=8,color="orange")
p2.add_tools(hover_tool)

velo = p2.circle(x="x", y="y", source=source1, size=7, color="blue", legend_label="Trafic Vélo")
pieton = p2.circle(x="x", y="y", source=source2, size=7, color="orange", legend_label="Trafic Piéton")
p2.legend[0].items=[]

# Creation de legende
legend = Legend(items=[
    LegendItem(label="Trafic Vélos et Piétons", renderers=[velo , pieton])
], location="top_right")

p2.add_layout(legend)

#####################################################
# graphique 3 :

legend_items = []
hover_tool = HoverTool(tooltips=[( 'Trafic vélo', '@trafic_velo'),
                                 ('Trafic piéton','@trafic_pieton')])
p3 = figure(title="Trafic vélos et piétons en fonction du numéro identifiant de la ville", y_range=Range1d(0, 100000),x_axis_label="Numéro identifiant de la ville", y_axis_label="Trafic",
           x_range=source1.data["ident_num"], tools="")
p3.vbar(x='ident_num', top='trafic_velo', source=source1, width=0.2)
p3.vbar(x='ident_num', top='trafic_pieton', color="orange", source=source1, width=0.2)

legend = Legend(items=legend_items)
p3.add_layout(legend, 'right')
legend.items = [    ( "Trafic vélo", [p3.renderers[0]] ),
    ( "Trafic piéton", [p3.renderers[1]] ),]
legend.click_policy="hide"
p3.add_tools(hover_tool)


###################################################
# graphique 4 : 
p4 = figure(x_axis_type="mercator", y_axis_type="mercator", active_scroll="wheel_zoom", title="Reseau Ferroviaire en Bretagne")
tile_provider = get_provider(OSM)
p4.add_tile(tile_provider)
p4.multi_line(xs="x",ys="y",color="red",source =source3,legend_label="Axe des trains")
hover_tool3 = HoverTool(tooltips=[( "Axe de train", '@axe')])
p4.add_tools(hover_tool3)

##################################################
# Partie 5 :
# chargement des données
ferroviaire = pd.read_csv("arrets-ferroviaires.csv",sep=";")
# traitement de données
data_ferro = ferroviaire.iloc[:, [12] + list(range(14, 17)) + list(range(18, 21))]
# Extraction des deux premiers chiffres du code INSEE pour obtenir le code département
data_ferro.loc[:, "code_departement"] = data_ferro["code_insee"].astype(str).str[:2]

# Agrégation des données par département
df_agg = data_ferro.groupby("code_departement").agg({"tgv": lambda x: x.eq("O").mean(), "guichet": lambda x: x.eq("O").mean(),"borne_dbr": lambda x: x.eq("O").mean(), "assist_pmr": lambda x: x.eq("O").mean(),"abri_velo": lambda x: x.eq("O").mean(), "park_voit": lambda x: x.eq("O").mean()})

# Renommage des colonnes
df_agg = df_agg.rename(columns={"borne_dbr": "borne_libre_service", "assist_pmr": "assistance_pmr", "abri_velo": "abritation_velo", "park_voit": "parking_voiture"})

df = df_agg.reset_index()
source5 = ColumnDataSource(df)


guichet = plot_bar_chart(df, 'guichet', 'Code département', 'Proportion ')
tgv = plot_bar_chart(df, 'tgv', 'Code département', 'Proportion ')
borne_dbr = plot_bar_chart(df, 'borne_libre_service', 'Code département', 'Proportion ')
assist_pmr = plot_bar_chart(df, 'assistance_pmr', 'Code département', 'Proportion')
abri_velo = plot_bar_chart(df, 'abritation_velo', 'Code département', 'Proportion ')
park_voit = plot_bar_chart(df, 'parking_voiture', 'Code département', 'Proportion ')


# Création de la grille
grid = gridplot([[guichet, tgv],[abri_velo,park_voit],[borne_dbr, assist_pmr]])

############################################################
############################################################
# Page 1 : 
div=Div(text="""<h1> Les reseaux de transport en Bretagne</h1>
<h2>Ibrahim SOILAHOUDINE - Nabil LOUDAOUI - Yann KIBAMBA</h2>
<p>La région Bretagne, située à l'ouest de la France, est une région qui dispose d'un réseau de transport bien développé. Elle offre différents moyens de transport pour les déplacements locaux et internationaux. Pour ce projet nous avons donc décider de porter un regard sur les différents moyens de transport de la région, aussi bien maritime que terrestre.</p>
<p>Pour cela, on a utilisé plusieurs bases de données de data.bretagne.bzh.</p>
<p>Ce sont les suivantes: trafic-ferries.csv, compteurs-cyclistespietons.csv et arrets-ferroviaires.csv</p>
<p>Ci-dessous, la représentation des chiffres du trafic ferries des ports de Roscoff et Saint-Malo en fonction des années.</p>""")
div2=Div(text="""<img src="https://static.actu.fr/uploads/2019/08/salamenca-960x640.jpg" width=500>""")
div3=Div(text="""Via ce graphique interractive en cliquant sur les années dans la légende, on remarque tous d'abord que le nombre de passagers augmente fortement lors de la période estivale avec un pic. De 2017 à 2019, le nombre de passagers est d'environ 250 000. Le graphique permet de remarquer la forte chute en 2020 dû à la crise sanitaire. 2021 et 2022 montre le regain de passagers mais reste encore un peu loin du nombre passagers de la fin des années 2010.""")
tab1=Panel(child=Column(div, row(p,Column(div2)),div3),title="Trafic ferries bretagne")

###################################################

# Page 2
div4=Div(text="""<h1> Compteurs cyclistes et piétons</h1>
<h3>Développé par la société éco-compteur, la technologie « Eco-MULTI » permet de mesurer la fréquentation par des capteurs. Cette technologie installé dans différentes communes de bretagne a enregistré le trafic de piéton et de vélo que nous avons représenter ci-dessous.</h3>
<p> Carte interactif représentant pour chaque ville les trafics de vélos et piétons, en cliquant sur chaque point. </p>""")
div5=Div(text="""<img src="https://www.lorientbretagnesudtourisme.fr/uploads/2019/05/e.-lemee-balade-la-voie-verte-59-jpeg-1024x683.jpg" width=500>""")
tab2=Panel(child=Column(div4, row(p2,Column(div5))),title="Compteurs cyclistes et pietons")

####################################################

# Page 3
div6=Div(text="""<h1> Compteurs cyclistes et piétons</h1>
<h3>Ci dessous, des diagrammes empilés représentant la part de cyclistes et piétons dans les villes. La supériorité de cyclistes par rapport aux piétons ou l'inverse, dépend de la ville.</h3>
<p> Il est possible en cliquant sur la legende de voir plus spécifiquement le nombre de piétons ou de cyclistes   </p>""")
div7=Div(text="""<img src="https://www.francevelotourisme.com/sites/default/files/medias/images/conseils/Pr%C3%A9parer%20mon%20voyage%20%C3%A0%20v%C3%A9lo/voie%20verte/velo-voie-verte.JPG" width=500>""")
tab3 = Panel(child=Column(div6, row(p3,Column(div7))), title="Trafic vélo et piéton")

####################################################

# Page 4 
div11=Div(text="""<h1> Cartographie des axes ferroviaires en Bretagne</h1>

<p>On remarque que le réseau ferroviaire passe principalement par les grandes villes de la régions (Rennes, Lorient ou encore Brest) et laisse un vide dans le centre. Le réseau ferroviraire priorise les grandes villes ainsi que les villes proches de la côte. Ces destinations mobilisent bien plus de voyageurs.</p>
<p>En somme, on peut retenir un réseau ferroviaire hétérogène.</p>""")
div12=Div(text="""<img src="https://www.letelegramme.fr/images/2021/01/11/la-gare-sncf-de-saint-brieuc-telle-qu-elle-existe_5479092_676x482p.jpg?v=1" width=550>""")
div13=Div(text="""On peut voir que le réseau ferroviaire de la Bretagne est très mal desservis. En effet, le réseau ferroviaire passe sur tout le tour de la Bretagne mais ne déssert pas du tout le centre de la Bretagne. Le réseau ferroviraire priorise les grandes villes ainsi que les villes proches de la mer car c'est pour ces destinations qu'il doit y avoir le plus de voyageurs, mais cela est au détriment du centre de la Bretagne qui se retrouve dans ligne ferroviaire à proximité.""")
tab4=Panel(child=Column(div11, Row(p4,Column(div12)),div13),title="Cartographie des axes ferroviaires en Bretagne")

#####################################################

# Page 5
div8=Div(text="""<h1> Caracteristique des gares dans les départements</h1>
<p> Dans une base de données constitué des différentes gares de la région avec leurs informations respectives, nous avons à l'aide d'un groupby réunis toutes les gares d'un même département en une seul ligne représentant le département. Ainsi ci-dessous, il est possible de voir la proportion des caractéristiques (les abris vélos ou encore les guichets) des gares pour chaque département en fonction des autres départements. </p>
<p>Par exemple,  on peut voir que pour les parkings de voiture, la proportion est de 1 pour tous les départements ce qui implique que toutes les gares de chaque départements dispose d'un parking. </p>
<p>On voit également qu'aucune gare du département 50 (La Manche ) ne dispose d'abri vélo ou de gare avec un tgv. En revanche la proportion de guichet est bien plus importante dans les gares de la Manche.</p>""")

tab5 = Panel(child= Column(div8, row(grid)), title="Caracteristique des gares dans les départements")
# Création des onglets
tabs = Tabs(tabs=[tab1, tab2,tab3,tab4,tab5 ])

#####################################################

# Affichage des onglets
show(tabs)
