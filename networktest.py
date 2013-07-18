import networkx as nx

G=nx.DiGraph()

def createGraph():
    #input: none
    #output: a directed graph of connected countries,
    #with edge weights defined by the troops in the target country
    for country in game["countries"]:
        for border in country["border countires"]:
            if country.owner!=border.owner:
                G.add_edge(country,border,weight=border.troops)
                G.add_edge(border,country,weight=country.troops)
            else:
                G.add_edge(country,border,weight=0)
                G.add_edge(border,country,weight=0)
    return G
        
def pathToCountry(source,target):
    #input: a source country and target country
    #output: a list of countries on the shortest path from source to target
    return nx.shortest_path(G,source,target,weight)
    
def shouldAttack(source,targets):
    #input: a source country and a list of target countries
    #output: a boolean indicating whether attacking is a good idea
    var f = source.troops
    var e = 0
    for country in targets:
        e += country.troops
    return (f>=(2*e+len(targets))
    
    
    
    