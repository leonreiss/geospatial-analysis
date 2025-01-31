############################ PIP ####################################
#Install in Terminal and confirm with enter
#pip install osmnx geopy networkx
#pip install osmnx
#pip install streamlit
#pip install tqdm
#pip install matplotlib
#pip install folium
#pip install scikit-learn
#pip install streamlit-folium

##### ARGUMENT for STREAMLIT: streamlit run /Users/leonreiss/Desktop/Navigation.py

############################ LIBRARIES ##############################
import networkx as nx
from tqdm import tqdm
import osmnx as ox
import matplotlib.pyplot as plt
import numpy as np
import logging
import time
from geopy.geocoders import Nominatim
import geopy.distance
import folium
import streamlit as st
from streamlit_folium import folium_static

############################### FUNCTION DEF ########################
@st.cache_data
def get_graph(place_name, network_type):
    return ox.graph_from_place(place_name, network_type=network_type)

# Convert address to nearest graph node
def get_nearest_node(graph, address):
    geolocator = Nominatim(user_agent="navigation_system")
    location = geolocator.geocode(address)
    if location:
        # Find the nearest node in the graph
        nearest_node = ox.distance.nearest_nodes(graph, X=location.longitude, Y=location.latitude)
        return nearest_node
    else:
        st.error(f"Address '{address}' not found.")
        return None

# Find the shortest route between two addresses
def get_shortest_route(graph, start_address, end_address):
    start_node = get_nearest_node(graph, start_address)
    end_node = get_nearest_node(graph, end_address)

    if start_node is None or end_node is None:
        return None, None

    try:
        route = nx.shortest_path(graph, source=start_node, target=end_node, weight='length')
        route_length = nx.shortest_path_length(graph, source=start_node, target=end_node, weight='length')
        return route, route_length
    except nx.NetworkXNoPath:
        return None, None

# Convert the entire graph to GeoJSON format
def graph_to_geojson(graph):
    nodes, edges = ox.graph_to_gdfs(graph)
    return edges.__geo_interface__

# Convert the route to GeoJSON format
def route_to_geojson(graph, route):
    # Extract the subgraph containing the edges of the route
    route_edges = ox.graph_to_gdfs(graph.subgraph(route), nodes=False, edges=True)
    return route_edges.__geo_interface__

########## Main function "plot_route_on_map" ########
    # This function plots the route on a Folium map, centering it on the midpoint of the route, 
    # which is calculated based on the coordinates of the start and end points. It also allows 
    # the user to choose between different map styles (e.g., Satellite, OpenStreetMap, Stamen Terrain).
    
    # The function converts the graph to GeoDataFrames, extracts the coordinates for the start 
    # and end nodes, and uses those coordinates to set the center of the map, ensuring the route 
    # is fully visible and appropriately zoomed in.
#####################################################
#####################################################

def plot_route_on_map(graph, route, start_address, end_address, map_style):
    # Convert into Geo-Data
    nodes, _ = ox.graph_to_gdfs(graph)
    
    # Calculate the centre point of the route (between start and end point)
    start_coords = nodes.loc[route[0]].geometry
    end_coords = nodes.loc[route[-1]].geometry
    center = [(start_coords.y + end_coords.y) / 2, (start_coords.x + end_coords.x) / 2]

    # Create the map and set the zoom level based on the route
    if map_style == 'Satellite':
        m = folium.Map(location=center, zoom_start=14, tiles='cartodb positron')  # Satellitenansicht
    elif map_style == 'OpenStreetMap':
        m = folium.Map(location=center, zoom_start=14, tiles='OpenStreetMap')  # OpenStreetMap
    elif map_style == 'Stamen Terrain':
        m = folium.Map(location=center, zoom_start=14, tiles='Stamen Terrain', 
                       attr='Map tiles by Stamen Design, under CC BY 3.0. Data by OpenStreetMap, under ODbL.')  # Stamen Terrain mit Attribution
    else:
        m = folium.Map(location=center, zoom_start=14, tiles='cartodb positron')  # Standardansicht

    # Add the street as GeoJSON
    folium.GeoJson(graph_to_geojson(graph), name='Street Network').add_to(m)

    # Add the route as GeoJSON
    folium.GeoJson(route_to_geojson(graph, route), name='Route',
                   style_function=lambda x: {'color': 'red', 'weight': 5}).add_to(m)

    # Add a PolyLine that follows the route
    route_coords = []
    for node in route:
        coords = nodes.loc[node].geometry
        route_coords.append([coords.y, coords.x])

    folium.PolyLine(route_coords, color='red', weight=5, opacity=0.7).add_to(m)

    # Add markers for start and end point
    start_node = get_nearest_node(graph, start_address)
    end_node = get_nearest_node(graph, end_address)

    if start_node:
        start_coords = nodes.loc[start_node].geometry
        folium.Marker(location=[start_coords.y, start_coords.x], popup=f"Start: {start_address}",
                      icon=folium.Icon(color='green')).add_to(m)

    if end_node:
        end_coords = nodes.loc[end_node].geometry
        folium.Marker(location=[end_coords.y, end_coords.x], popup=f"End: {end_address}",
                      icon=folium.Icon(color='red')).add_to(m)

    # Füge Layer Control hinzu
    folium.LayerControl().add_to(m)

    return m

#####################################################################
###################### MAIN PROCESS #################################
place_name = "Aachen, Germany"
network_type = 'drive'

# Streamlit interface
st.title("Route Finder in Aachen")
start_address = st.text_input("Enter the starting address:")
end_address = st.text_input("Enter the destination address:")

# Dropdown for map style selection
map_style = st.selectbox("Select map style:", ["Satellite", "OpenStreetMap", "Street"])

# "Calculate Route" button
calculate_button = st.button("Calculate Route")

# Only proceed if both addresses are entered
if start_address and end_address and calculate_button:
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    # Start timer
    start_time = time.time()

    st.write(f"Downloading street network for {place_name}...")

    # Access the cached graph
    graph = get_graph(place_name, network_type)

    # Calculate elapsed time
    elapsed_time = time.time() - start_time
    st.write(f"Finished downloading the network. Elapsed time: {elapsed_time:.2f} seconds.")

    # Calculate the route
    route, route_length = get_shortest_route(graph, start_address, end_address)

    if route:
        st.write(f"Found route: {route}")
        st.write(f"Total route length: {route_length} meters")

        # Visualize the route on a map
        m = plot_route_on_map(graph, route, start_address, end_address, map_style)
        st.write("Route visualization:")
        folium_static(m)  # Display the Folium map

    else:
        st.error("No route found.")
