import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import folium_static, st_folium
import branca.colormap as cm
import json
from shapely.geometry import Point

# Set the page title and layout
st.set_page_config(
    page_title="Pierce County Sites Visualization",
    layout="wide"
)

sites_path = r'.\AppData\Sites_with_Clusters.shp'
sites = gpd.read_file(sites_path)
sites = sites.to_crs('EPSG:4326')
sites = sites.rename(columns={'Nearby_Cou': 'Nearby_Count_500',
                              'Nearby_C_1': 'Nearby_Count_1000',
                              'Nearby_C_2': 'Nearby_Count_2000',
                              'Nearby_C_3': 'Nearby_Count_3000',
                              'Nearest_Tr':'Nearest_Transit_Distance', 
                              'Nearest_Ro':'Nearest_Road_Distance'}) # strange saving issue with the shapefile

calls = pd.read_csv(r'.\AppData\Overdose_zip_geocodio.csv')
calls = gpd.GeoDataFrame(calls, geometry=gpd.points_from_xy(calls.Longitude, calls.Latitude), crs='EPSG:4326')


# App title
st.title("Pierce County Sites Visualization")

# Create layout with columns
col1, col2 = st.columns([7, 3])

# Sidebar for filtering
with st.sidebar:
    st.header("Filter Options")
    
    # Cluster selection
    selected_clusters = st.multiselect(
        "Select Clusters to Highlight:",
        options=[1, 2, 3],
        default=None
    )
    
    # Option to display calls data
    show_calls = st.checkbox("Show Call Data Points", value=False)
    
    # Additional filters
    st.markdown("---")
    st.markdown("### Map Information")
    st.markdown("- Hover over points to see basic information")
    st.markdown("- Click on points to view detailed information in the side panel")
    st.markdown("- Use the cluster filter to highlight specific groups")
    st.markdown("- Toggle call data points to view service call locations")

# Initialize session state to store the selected site
if 'selected_site_id' not in st.session_state:
    st.session_state.selected_site_id = None

# Filter the data based on selection
if selected_clusters:
    filtered_sites = sites[sites['Cluster'].isin(selected_clusters)]
    map_sites = sites  # Keep all sites for the map, but highlight filtered ones
else:
    filtered_sites = sites
    map_sites = sites

# Create the map
with col1:
    # Create a folium map centered on Pierce County
    m = folium.Map(
        location=[47.2, -122.4],  # Pierce County coordinates
        zoom_start=10,
        tiles="OpenStreetMap"
    )
    
    # Create color maps
    site_colors = {
        1: '#2e5777',  # Deep blue-gray
        2: '#0194d3',  # Bright blue
        3: '#3d7527'   # Earthy green
    }
    
    call_colors = {
        1: '#FF0000',  # Red for high priority
        2: '#FF9800',  # Orange for medium priority
        3: '#4CAF50'   # Green for low priority
    }
    
    # Create feature groups
    site_groups = {
        1: folium.FeatureGroup(name="Cluster 1 Sites"),
        2: folium.FeatureGroup(name="Cluster 2 Sites"),
        3: folium.FeatureGroup(name="Cluster 3 Sites")
    }
    
    calls_group = folium.FeatureGroup(name="Service Calls")
    
    # Add site points to the map with unique IDs
    for idx, site in map_sites.iterrows():
        # Determine if this point should be highlighted
        is_highlighted = selected_clusters and site['Cluster'] in selected_clusters
        
        # Set marker properties based on highlighting
        marker_color = site_colors[site['Cluster']]
        marker_opacity = 1.0 if is_highlighted or not selected_clusters else 0.4
        marker_radius = 8 if is_highlighted or not selected_clusters else 6
        
        # Create tooltip content
        tooltip_html = f"""
        <div style="font-family: Arial; font-size: 12px;">
            <b>{site['Type']}</b><br>
            {site['Address']}, {site['City']}<br>
            Cluster: {site['Cluster']}
        </div>
        """
        
        # Create a unique ID for each site marker for click handling
        site_id = f"site_{idx}"
        
        # Add the marker to the appropriate cluster group
        circle = folium.CircleMarker(
            location=[site.geometry.y, site.geometry.x],
            radius=marker_radius,
            color=marker_color,
            fill=True,
            fill_color=marker_color,
            fill_opacity=marker_opacity,
            opacity=marker_opacity,
            tooltip=folium.Tooltip(tooltip_html),
        )
        
        # Add site ID to the marker as a custom property
        circle.add_to(site_groups[site['Cluster']])
        
        # Add onclick JavaScript to set a hidden input field with the site ID
        circle.add_child(folium.Element(f"""
            <script>
            var el = document.querySelector('circle:last-child');
            el.setAttribute('id', '{site_id}');
            el.onclick = function() {{
                // Use Streamlit's setComponentValue to pass back the ID
                if (window.parent.streamlitApp) {{
                    window.parent.streamlitApp.setComponentValue('{site_id}');
                }}
            }};
            </script>
        """))
    
    # Add call points to the map if enabled
    if show_calls:
        for idx, call in calls.iterrows():
            # Set marker properties
            marker_color = 'black'
            # Create tooltip content
            #tooltip_html = f"""
            #<div style="font-family: Arial; font-size: 12px;">
            #    <b>Call ID:</b> {call['Call_ID']}<br>
            #    <b>Type:</b> {call['Type']}<br>
            #    <b>Date:</b> {call['Date']}<br>
            #    <b>Priority:</b> {call['Priority']}
            #</div>
            #"""
            
            # Add star markers for calls
            folium.CircleMarker(
                location=[call.geometry.y, call.geometry.x],
                radius=2,  # smaller than site markers
                color='black',
                fill=True,
                fill_color='black',
                fill_opacity=0.4,
                opacity=0.4,
                #tooltip=folium.Tooltip(tooltip_html),
            ).add_to(calls_group)
    
    # Add all feature groups to the map
    for cluster_id, feature_group in site_groups.items():
        feature_group.add_to(m)
    
    if show_calls:
        calls_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
    # Create a legend
    legend_html = '''
    <div style="position: fixed; bottom: 50px; left: 50px; z-index:9999; 
                background-color: white; padding: 10px; border-radius: 5px; 
                border: 1px solid grey; font-family: Arial; font-size: 12px;">
        <p style="margin-bottom: 5px;"><b>Legend:</b></p>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color: #1E88E5; width: 15px; height: 15px; 
                 border-radius: 50%; margin-right: 5px;"></div>
            <span>Cluster 1 Sites</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color: #FFC107; width: 15px; height: 15px; 
                 border-radius: 50%; margin-right: 5px;"></div>
            <span>Cluster 2 Sites</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color: #D81B60; width: 15px; height: 15px; 
                 border-radius: 50%; margin-right: 5px;"></div>
            <span>Cluster 3 Sites</span>
        </div>
    '''
    
    # Add call legend items if needed
    if show_calls:
        legend_html += '''
        <div style="margin-top: 8px; margin-bottom: 5px;"><b>Service Calls:</b></div>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <i class="fa fa-phone" style="color: black; margin-right: 5px;"></i>
            <span>Call Location</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color: #FF0000; width: 15px; height: 15px; 
                 margin-right: 5px;"></div>
            <span>Priority 1</span>
        </div>
        <div style="display: flex; align-items: center; margin-bottom: 3px;">
            <div style="background-color: #FF9800; width: 15px; height: 15px; 
                 margin-right: 5px;"></div>
            <span>Priority 2</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="background-color: #4CAF50; width: 15px; height: 15px; 
                 margin-right: 5px;"></div>
            <span>Priority 3</span>
        </div>
        '''
    
    legend_html += '</div>'
    m.get_root().html.add_child(folium.Element(legend_html))
    
    # Display the map and capture click events
    map_data = st_folium(m, width=800, height=600, returned_objects=["last_object_clicked"])
    
    # Process click events
    if map_data.get("last_object_clicked") is not None:
        click_lat = map_data["last_object_clicked"]["lat"]
        click_lng = map_data["last_object_clicked"]["lng"]

        # Find the closest site based on lat/lng match
        for idx, row in sites.iterrows():
            site_lat = row.geometry.y
            site_lng = row.geometry.x
            if abs(site_lat - click_lat) < 1e-6 and abs(site_lng - click_lng) < 1e-6:
                st.session_state.selected_site_id = idx
                break
    
    # Add information about the dataset
    st.markdown(f"**Total Sites:** {len(sites)}")
    if selected_clusters:
        st.markdown(f"**Currently Highlighted:** {len(filtered_sites)} sites in Clusters {', '.join(map(str, selected_clusters))}")
    if show_calls:
        st.markdown(f"**Service Calls Displayed:** {len(calls)}")

# Display site details in the right panel
with col2:
    st.header("Site Details")
    
    if st.session_state.selected_site_id is not None:
        # Get the selected site
        selected_site = sites.iloc[st.session_state.selected_site_id]
        
        # Display the site details
        st.subheader(f"{selected_site['Type']} Site")
        st.markdown(f"**Address:** {selected_site['Address']}")
        st.markdown(f"**City:** {selected_site['City']}")
        
        # Show cluster with colored badge
        cluster_color = site_colors[selected_site['Cluster']]
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="margin-right: 8px;"><b>Cluster:</b></span>
                <span style="background-color: {cluster_color}; color: white; 
                      padding: 3px 8px; border-radius: 10px; font-weight: bold;">
                    {selected_site['Cluster']}
                </span>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        # Create expandable sections for detailed information
        with st.expander("Proximity Information", expanded=True):
            cols = st.columns(2)
            with cols[0]:
                st.metric("Calls within 500m", selected_site['Nearby_Count_500'])
                st.metric("Calls within 2000m", selected_site['Nearby_Count_2000'])
            with cols[1]:
                st.metric("Calls within 1000m", selected_site['Nearby_Count_1000'])
                st.metric("Calls within 3000m", selected_site['Nearby_Count_3000'])
        
        with st.expander("Distance Information", expanded=True):
            cols = st.columns(2)
            with cols[0]:
                st.metric("Nearest Transit (Meters)", f"{selected_site['Nearest_Transit_Distance']}m")
            with cols[1]:
                st.metric("Nearest Main Road (Meters)", f"{selected_site['Nearest_Road_Distance']}m")
        
        # Display coordinates
        with st.expander("Geospatial Information", expanded=False):
            st.markdown(f"**Latitude:** {selected_site.geometry.y:.6f}")
            st.markdown(f"**Longitude:** {selected_site.geometry.x:.6f}")
        
        # Add a button to clear selection
        if st.button("Clear Selection"):
            st.session_state.selected_site_id = None
            st.rerun()
    else:
        st.info("👈 Click on a site on the map to view its details here.")