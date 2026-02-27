"""
    Project: Hellas Grid Monitor
    Description: A real-time dashboard for monitoring the Greek electricity grid, that fetches data from ENTSO-E Transparency Platform and OpenWeatherMap API.
    Author: Dimitrios Poulos
"""


import streamlit as st    # Core framework for building the interactive web dashboard UI
import pandas as pd    # Used for data manipulation
import plotly.express as px    # Used for visualizations
import plotly.graph_objects as go    # Used for custom visualizations
from entsoe import EntsoePandasClient    # Official API client to retrieve grid data from the ENTSO-E platform
from datetime import datetime, timedelta    # Used for managing dates and time and calculating date ranges
import requests    # Used for making HTTP requests (in our case to the OpenWeatherMap API)



# API Configuration
ENTSOE_token = st.secrets["ENTSOE_token"]
ENTSOE_client = EntsoePandasClient(api_key=ENTSOE_token)
EIC_GR = "10YGR-HTSO-----Y"    # EIC code for Greece

OWM_token = st.secrets["OWM_token"]



st.set_page_config(page_title="Hellas Grid Monitor", layout="wide", initial_sidebar_state="expanded")    # Sets the page title and layout



# Color mapping for energy sources
color_mapping = {
        'Wind Onshore': '#2E8B57',
        'Solar': '#FFD700',
        'Hydro Water Reservoir': '#1F77B4',
        'Hydro Run-of-river and poundage': '#6EC1E4',
        'Biomass': '#A5C45B',
        'Geothermal': '#808080',
        'Fossil Hard coal': '#93308C',
        'Fossil Brown coal/Lignite': '#D81C33',
        'Fossil Gas': '#D71F84',
    }



# Data fetching functions
# Function to load generation data
@st.cache_data(ttl=900)    # Caches the API response for 15 minutes (900 seconds) to prevent issues with the API
def get_generation_data(start_date, end_date):
    start_time = pd.Timestamp(start_date, tz='Europe/Athens')    # Converts the input start date to a pandas Timestamp with the Greek timezone
    end_time = pd.Timestamp(end_date, tz='Europe/Athens') + timedelta(days=1) - timedelta(seconds=1)    # Converts end date to Timestamp and sets the time to the last second of the day
    dataFrame_generation = ENTSOE_client.query_generation(EIC_GR, start=start_time, end=end_time)    # Variable to store the generation data
    last_row = dataFrame_generation.dropna().iloc[-1]    # Removes any rows with missing data and extracts the very last row (the most recent data)
    data_time = last_row.name
    latest_value = last_row.rename_axis('Source').reset_index(name='MW')    # Formats the extracted row into a clean DataFrame
    
    return dataFrame_generation, latest_value, data_time



# Function to load consumption data
@st.cache_data(ttl=900)
def get_consumption_data(start_date, end_date):
    start_time = pd.Timestamp(start_date, tz='Europe/Athens')
    end_time = pd.Timestamp(end_date, tz='Europe/Athens') + timedelta(days=1) - timedelta(seconds=1)
    dataFrame_consumption = ENTSOE_client.query_load(EIC_GR, start=start_time, end=end_time)    # Variable to store the consumption data
    
    return dataFrame_consumption



# Function to load live price data
def get_price_data(start_date, end_date):
    start_time = pd.Timestamp(start_date, tz='Europe/Athens')
    end_time = pd.Timestamp(end_date, tz='Europe/Athens') + timedelta(days=1) - timedelta(seconds=1)
    try:
        dataFrame_price = ENTSOE_client.query_day_ahead_prices(EIC_GR, start=start_time, end=end_time)    # Variable to store the price data
        return dataFrame_price
    except Exception as e:
        st.error(f"Error fetching price data: {e}")
        return pd.DataFrame()    # Return an empty DataFrame if there's an error



# Function to get live weather data for a given location and plant type
@st.cache_data(ttl=900)
def get_weather_data(lat, lon, plant_type):
    try:
        weather_url = f"http://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_token}&units=metric"    # Constructs OpenWeatherMap API URL with metric units
        weather_data = requests.get(weather_url).json()    # Sends GET request and parses the JSON response
        temperature = weather_data['main']['temp']    # Extracts temperature
        wind_speed = weather_data['wind']['speed']    # Extracts wind speed
        cloud_cover = weather_data['clouds']['all']    # Extracts cloud cover

        if plant_type == 'Solar':
            if cloud_cover > 80:
                status = "Low Solar Output (Cloudy)"
            elif cloud_cover > 50:
                status = "Moderate Solar Output (Partly Cloudy)"
            else:
                status = "High Solar Output (Clear)"
        elif plant_type == 'Wind':
            if wind_speed < 3:
                status = "Low Wind Output (Calm)"
            elif wind_speed < 8:
                status = "Moderate Wind Output"
            else:
                status = "High Wind Output (Windy)"
        else:
            status = "-"

        weather_info = f"{temperature}°C, {cloud_cover}% cloud cover, {wind_speed} m/s wind speed"    # Formats all weather variables into a single display string
        return weather_info, status
    
    except Exception as e:
        return "-", "-"



# Function to load generation forecast data
@st.cache_data(ttl=900)
def get_generation_forecast(start_date, end_date):
    start_time = pd.Timestamp(start_date, tz='Europe/Athens')
    end_time = pd.Timestamp(end_date, tz='Europe/Athens') + timedelta(days=1) - timedelta(seconds=1)
    try:
        dataFrame_generation_forecast = ENTSOE_client.query_generation_forecast(EIC_GR, start=start_time, end=end_time)    # Variable to store the generation forecast data
        return dataFrame_generation_forecast
    except Exception as e:
        st.error(f"Error fetching generation forecast data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error



# Function to load consumption forecast data
@st.cache_data(ttl=900)
def get_consumption_forecast(start_date, end_date):
    start_time = pd.Timestamp(start_date, tz='Europe/Athens')
    end_time = pd.Timestamp(end_date, tz='Europe/Athens') + timedelta(days=1) - timedelta(seconds=1)
    try:
        dataFrame_consumption_forecast = ENTSOE_client.query_load_forecast(EIC_GR, start=start_time, end=end_time)    # Variable to store the consumption forecast data
        return dataFrame_consumption_forecast
    except Exception as e:
        st.error(f"Error fetching consumption forecast data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame if there's an error




# Sidebar Configuration
st.sidebar.title("Hellas Grid Monitor")

box1 = st.sidebar.empty()    # Placeholder for the data timestamp
box2 = st.sidebar.container()    # Placeholder for the refresh button
st.sidebar.divider()
box3 = st.sidebar.empty()    # Placeholder for the time filters

with box3:
    st.subheader("Date Filters")
    col_1, col_2 = st.sidebar.columns(2)
    default_start_date = datetime.now() - timedelta(days=1)
    default_end_date = datetime.now()
    today = datetime.now().date()
    with col_1:
        start_date = st.date_input("Start Date: ", value=default_start_date, max_value=today)    # Used as max value to prevent future date selection
    with col_2:
        end_date = st.date_input("End Date: ", value=default_end_date, max_value=today)


dataFrame_generation, latest_value, data_time = get_generation_data(start_date=start_date, end_date=end_date)

dataFrame_consumption = get_consumption_data(start_date=start_date, end_date=end_date)

dataFrame_price = get_price_data(start_date=start_date, end_date=end_date)
if not dataFrame_price.empty:
    latest_price = dataFrame_price.iloc[-1]    # Variable to store the latest price in EUR/MWh
else:
    latest_price = None    # If no price data is available, set latest_price to None

forecast_start = datetime.now().date()
forecast_end   = datetime.now().date() + timedelta(days=1)
dataFrame_generation_forecast = get_generation_forecast(start_date=forecast_start, end_date=forecast_end)
dataFrame_consumption_forecast = get_consumption_forecast(start_date=forecast_start, end_date=forecast_end)

box1.markdown(f"**Data Timestamp:** \n{data_time.strftime('%H:%M %d/%m/%Y')}")

with box2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()    # Clears all cached data in order to make a API call
        st.rerun()


st.sidebar.markdown("-----")


st.sidebar.markdown("#### Export Data")
generation_data_csv = dataFrame_generation.to_csv(sep=';', decimal=',', index_label='Datetime', encoding='utf-8-sig')    # Convert generation data to CSV format (for Excel)
st.sidebar.download_button(
    label="Download Generation Data (CSV)",
    data=generation_data_csv,
    file_name=f"Hellas_Grid_{start_date}_to_{end_date}.csv",
    mime='text/csv',
    use_container_width=True
)


st.sidebar.markdown("-----")



total_generation_MW = latest_value['MW'].sum()    # Variable to store the total generation in MW (Active Power)

renewable_generation = ['Wind Onshore', 'Solar', 'Hydro Water Reservoir', 'Biomass']    # List of renewable energy sources
renewable_generation_MW = latest_value[latest_value['Source'].isin(renewable_generation)]['MW'].sum()    # Variable to store the total renewable generation in MW (Active Power)
renewable_percentage = (renewable_generation_MW/total_generation_MW)*100    # Variable to store the percentage of renewable generation in relation to total generation


lignite_generation_MW = latest_value[latest_value['Source']=='Fossil Brown coal/Lignite']['MW'].sum()    # Variable to store the lignite generation in MW (Active Power)
lignite_percentage = (lignite_generation_MW/total_generation_MW)*100    # Variable to store the percentage of lignite generation in relation to total generation

natural_gas_generation_MW = latest_value[latest_value['Source']=='Fossil Gas']['MW'].sum()    # Variable to store the natural gas generation in MW (Active Power)
natural_gas_percentage = (natural_gas_generation_MW/total_generation_MW)*100    # Variable to store the percentage of natural gas generation in relation to total generation

co2_emissions = ((lignite_generation_MW*1000) + (natural_gas_generation_MW*400)) / total_generation_MW    # Variable to store the average CO2 emissions in kg/MWh, assuming lignite emits 1000 kg/MWh and natural gas emits 400 kg/MWh
co2_emissions_percentage = (co2_emissions/1000)*100    # Variable to store the CO2 emissions as a percentage of 1000 kg/MWh for the progress bar




st.sidebar.markdown("#### Quick Live Mix Overview")
st.sidebar.markdown(f"⚡ **Total Generation:** {total_generation_MW:.1f} MW")
st.sidebar.markdown(f"🌿 **Renewable Energy:** {renewable_percentage:.1f}%")
st.sidebar.progress(int(renewable_percentage))
st.sidebar.markdown(f"⚫ **CO2 Emissions:** {co2_emissions:.1f} kg/MWh")
st.sidebar.progress(int(co2_emissions_percentage))
st.sidebar.markdown(f"🏭 **Lignite:** {lignite_percentage:.1f}%")
st.sidebar.progress(int(lignite_percentage))
st.sidebar.markdown(f"🔥 **Natural Gas:** {natural_gas_percentage:.1f}%")
st.sidebar.progress(int(natural_gas_percentage))





st.markdown("<h1 style='text-align: center; font-size: 60px;'>Hellas Grid Monitor</h1>", unsafe_allow_html=True)    # Enable HTML parsing (unsafe_allow_html) to apply custom CSS for title
st.markdown("### Real-time Power Generation")

col1, col2, col3 = st.columns(3)    # Creates 3 columns for data
with col1.container(border=True):
    st.metric("Total Generation (MW)", f"{total_generation_MW} MW")
with col2.container(border=True):
    st.metric("RES Generation (%)", f"{renewable_percentage:.1f}%")
with col3.container(border=True):
    st.metric("Lignite Generation (%)", f"{lignite_percentage:.1f}%")

col4, col5, col6 = st.columns(3)
with col4.container(border=True):
    st.metric("Natural Gas Generation (%)", f"{natural_gas_percentage:.1f}%")
with col5.container(border=True):
    st.metric("CO2 Emissions (kg/MWh)", f"{co2_emissions:.1f} kg/MWh")
with col6.container(border=True):
    if latest_price is not None:
        st.metric("Day-Ahead Price (EUR/MWh)", f"{latest_price:.2f} €/MWh")
    else:
        st.metric("Day-Ahead Price (EUR/MWh)", "N/A")


st.markdown("-----")


tab1, tab2, tab3, tab4 = st.tabs(["Live Data", "24h Trends", "Map", "Forecasts"])
# Tab 1: Live Data for generation and grid analysis
with tab1:
    st.markdown("### Live Generation Mix and Network Analysis", help="Breakdown of current energy mix and an evaluation of the grid's green energy share.")
    col_left, col_right = st.columns([2, 1])
    # Left column for generation pie chart
    with col_left:
        st.markdown(f"#### Power Generation by Source")
        pie_chart = px.pie(latest_value, values='MW', names='Source', color='Source',color_discrete_map=color_mapping, title=f"Live Generation Mix ({data_time.strftime('%H:%M')})", hole=0.2)
        pie_chart.update_layout(
            height=400,
            margin=dict(l=10, r=10, t=50, b=10),
            legend=dict(orientation="h", yanchor="top", y=-0.2, xanchor="center", x=0.5)
        )
        st.plotly_chart(pie_chart, use_container_width=True)


    # Right column for network analysis and recommendations
    with col_right:
        st.markdown("#### Network Analysis")
        if renewable_percentage > 50:
            gauge_color = "green"
            st.success("The network is mostly green right now!")
        elif renewable_percentage > 20:
            gauge_color = "orange"
            st.warning("The network has a moderate share of renewables.")
        else:
            gauge_color = "red"
            st.error("The network is heavily reliant on fossil fuels.")
        if lignite_percentage > 30:
            st.error(f"Lignite generation ({lignite_percentage:.1f}%) is very high! Consider reducing it.")
        
        st.divider()
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = renewable_percentage,
            domain = {'x': [0.15, 0.85], 'y': [0.1, 0.9]},
            title = {'text': "Green (Renewable) Energy Share (%)", 'font': {'size': 18}},
            number = {'font': {'size': 30}},
            gauge ={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": "darkblue", "tickfont": {"size": 15}, "dtick": 10},
                "bar": {"color": gauge_color, "thickness": 0.5, "line": {"color": "rgba(255, 255, 255, 0.2)", "width": 1}},
                "bgcolor": "rgba(255, 255, 255, 0.08)",
                "borderwidth": 0,
            }
        ))
        fig_gauge.update_layout(height=300, margin=dict(t=50, b=0, l=0, r=0), paper_bgcolor="rgba(0,0,0,0)", font={'color': "white", 'family': "Arial"})
        st.plotly_chart(fig_gauge, use_container_width=True)






# Tab 2: Analysis of grid in a 24-hours period
with tab2:
    st.markdown("### 24-Hour Generation Trend (MW)", help="Evolution of power generation by energy source over the last 24 hours.")
    # The entire dataFrame_generation is used because it contains 24-hour data
    # fillna(0) ensures that there are no gaps in the graph
    fig_area = px.area(
        dataFrame_generation.fillna(0), 
        labels={'value': 'MW', 'index': 'Time'},
        title="Evolution of Generation per Source (Last 24h)",
        color_discrete_map=color_mapping
    )
    # Display optimization
    fig_area.update_layout(legend_title_text='Energy Source', xaxis_title="Time", yaxis_title="Power (MW)")
    fig_area.update_xaxes(tickformat="%H:%M")
    st.plotly_chart(fig_area, use_container_width=True)
    # Displays the data table
    with st.expander("See Data Table"):
        display_dataFrame_generation = dataFrame_generation.copy()
        display_dataFrame_generation.index = display_dataFrame_generation.index.strftime('%Y-%m-%d %H:%M')    # Date formatting
        st.dataframe(display_dataFrame_generation, use_container_width=True)
    

    st.markdown("-----")


    # Display of the demand curve (24-hour load) in a line chart
    st.markdown("### Demand Curve (24-hour Load)", help="Total electricity consumption (load) of the Greek grid over the last 24 hours.")
    if not dataFrame_consumption.empty:
        consumption_series = dataFrame_consumption.iloc[:, 0]    # Assuming the consumption data is in the first column
        # Identification of consumption's max/min values
        max_consumption = consumption_series.max()
        min_consumption = consumption_series.min()
        # Identification of times that consumption has max/min value
        max_consumption_time = consumption_series.idxmax().strftime('%H:%M')
        min_consumption_time = consumption_series.idxmin().strftime('%H:%M')
        col1, col2 = st.columns(2)
        with col1.container(border=True):
            st.metric(f"Max Consumption (at {max_consumption_time})", f"{max_consumption:.2f} MW")
        with col2.container(border=True):
            st.metric(f"Min Consumption (at {min_consumption_time})", f"{min_consumption:.2f} MW")
        
        # Display of consumption evolution in a chart
        fig_consumption = px.line(dataFrame_consumption, labels={'value': 'MW', 'index': 'Time'}, title="Demand Curve Evolution (Last 24h)")
        fig_consumption.update_layout(xaxis_title="Time", yaxis_title="Consumption (MW)", margin=dict(t=50, b=10, l=10, r=10), showlegend=False, height=300)
        st.plotly_chart(fig_consumption, use_container_width=True)

    else:
        st.warning("No consumption data available for the selected date range.")
    

    st.markdown("-----")


    st.markdown("### Day-Ahead Price Trend (Last 24h)", help="Wholesale electricity prices for the last 24 hours, as determined in yesterday's Day-Ahead Market.")
    if not dataFrame_price.empty:
        # Identification of price's max/min values
        max_price = dataFrame_price.max()
        min_price = dataFrame_price.min()
        # Identification of times that price has max/min value
        max_time = dataFrame_price.idxmax().strftime('%H:%M')
        min_time = dataFrame_price.idxmin().strftime('%H:%M')
        col1, col2 = st.columns(2)
        with col1.container(border=True):
            st.metric(f"Max Price (at {max_time})", f"{max_price:.2f} €/MWh")
        with col2.container(border=True):
            st.metric(f"Min Price (at {min_time})", f"{min_price:.2f} €/MWh")

        # Display of price evolution in a chart
        fig_price = px.line(dataFrame_price, labels={'value': 'EUR/MWh', 'index': 'Time'}, title="Day-Ahead Price Evolution (Last 24h)")
        fig_price.update_layout(xaxis_title="Time", yaxis_title="Price (EUR/MWh )", margin=dict(t=50, b=10, l=10, r=10), showlegend=False, height=300)
        st.plotly_chart(fig_price, use_container_width=True)

    else:
        st.warning("No price data available for the selected date range.")






# Tab 3: Interactive Energy Map of major Greek plants
with tab3:
    st.markdown("### Greece Energy Map", help="Geographical distribution of major power plants in Greece, including real-time weather data at their locations.")
    # Database containing geographical and technical information of Greek power plants
    map_locations = pd.DataFrame({
        "Name": [
                "Agios Dimitrios Power Station", "Megalopolis Power Station", "Kardia Power Station", "Ptolemaida V Power Station",
                "Agios Nikolaos Power Station", "Lavrio Power Station",
                "Kremasta Dam", "Thisavros Dam", "Kastraki Dam", "Plastiras Dam", "Stratos Dam",
                "Kafireas Wind Farm", "Panachaiko Wind Farm", "Soros Wind Farm",
                "Kozani Solar Park", "Amyntaio Solar Park", "Ptolemaida Solar Park", "Naoussa Solar Park"],
        "Type": [
                "Lignite", "Lignite", "Lignite", "Lignite",
                "Natural Gas", "Natural Gas",
                "Hydro", "Hydro", "Hydro", "Hydro", "Hydro",
                "Wind", "Wind", "Wind",
                "Solar", "Solar", "Solar", "Solar"],
        "Lat": [
                40.392, 37.416, 40.408, 40.480,
                38.358, 37.746,
                38.886, 41.354, 38.741, 39.235, 38.675,
                38.050, 38.232, 41.074,
                40.339, 40.696, 40.510, 40.630],
        "Lon": [
                21.928, 22.109, 24.784, 21.726,
                22.688, 24.066,
                21.495, 24.366, 21.364, 21.746, 21.325,
                24.501, 21.868, 25.952,
                21.780, 21.630, 21.720, 22.100],
        "Operator": [
                    "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)",
                    "Mytilineos", "Mytilineos",
                    "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)", "Public Power Corporation (PPC-DEI)",
                    "Enel GreenPower", "Acciona Energia", "Enel GreenPower",
                    "HELLENiQ ENERGY", "Meton Energy", "PPC Renewables", "Volterra"],
        "Capacity (MW)": [
                        1500, 846, 1200, 660,
                        1604, 914,
                        437, 384, 320, 130, 150,
                        154.1, 48, 11.7,
                        204, 450, 550, 14],
        "Description": [
                       "The historically largest lignite power plant in Greece.",
                       "Historic lignite center in the Peloponnese.",
                       "Large lignite plant in the Ptolemaida basin.",
                       "Greece's newest and most modern lignite unit.",
                       "Large combined-cycle natural gas plant in Boiotia.",
                       "Modern combined-cycle natural gas plant near Lavrio, Attica.",
                       "The largest hydroelectric dam in Greece (Achelous River).",
                       "Important hydroelectric project on the Nestos River.",
                       "Hydroelectric dam on the Acheloos River, Etoloakarnania.",
                       "Scenic hydroelectric dam on the Tavropos River, Thessaly.",
                       "Run-of-river hydroelectric plant on the lower Acheloos River.",
                       "Large wind farm complex in Evia, Central Greece.",
                       "The largest wind farm in the Peloponnese.",
                       "Small wind farm in Eastern Macedonia and Thrace.",
                       "One of the largest solar parks in Europe.",
                       "New solar park located in former lignite mines, Amyntaio.",
                       "New solar park on reclaimed lignite land, Ptolemaida.",
                       "Solar park in the Imathia region, Central Macedonia."]
    })

    weather_results = map_locations.apply(lambda row: get_weather_data(row['Lat'], row['Lon'], row['Type']), axis=1)    # Applies the get_weather_data function row-by-row using plant coordinates
    map_locations['Live Weather'] = [result[0] for result in weather_results]    # Extracts the weather info from the function results (result[0] contains the meteorological string)
    map_locations['Status'] = [result[1] for result in weather_results]    # Extracts the status info from the function results (result[1] contains the evaluated operational status)

    map_color_mapping = {"Lignite": "#D81C33",
        "Natural Gas": "#D71F84",
        "Hydro": "#1F77B4",
        "Wind": "#2E8B57",
        "Solar": "#FFD700"}

    # Change of map appearance via radio buttons
    map_style_choice = st.radio("Map Style:",
                                options=["Light Mode", "Satellite", "Dark Mode"],
                                horizontal=True)
    if map_style_choice == "Light Mode":
        mapbox_style = "carto-positron"
    elif map_style_choice == "Satellite":
        mapbox_style = "open-street-map"
    else:    mapbox_style = "carto-darkmatter"

    # Scatter Mapbox configuration with custom_data for interactive hover tooltips
    fig_map = px.scatter_mapbox(map_locations,
                                lat="Lat",
                                lon="Lon",
                                color="Type",
                                color_discrete_map=map_color_mapping,
                                size_max=15,
                                zoom=5,
                                height=500,
                                hover_name="Name",
                                custom_data = ["Operator", "Capacity (MW)", "Live Weather", "Status", "Description"])

    fig_map.update_layout(mapbox_style=mapbox_style, margin={"r":0,"t":50,"l":0,"b":0}, legend_title_text='Energy Type')
    # Custom hover template to display data of plants
    fig_map.update_traces(marker=dict(size=12), hovertemplate=("<b>%{hovertext}</b><br>" +
                                                        "Operator: %{customdata[0]}<br>" +
                                                        "Capacity: %{customdata[1]} MW<br>" +
                                                        "Live Weather: %{customdata[2]}<br>" +
                                                        "Status: %{customdata[3]}<br>" +
                                                        "Description: %{customdata[4]}"))
    st.plotly_chart(fig_map, use_container_width=True)






# Tab 4: 24-hour generation and consumption forecasts from ENTSO-E
with tab4:
    # Generation Forecast
    st.markdown("### Generation Forecast for the next 24 Hours", help="ENTSO-E predictions for total power generation for the upcoming day.")
    st.caption(f"Forecast period: {datetime.now().strftime('%d/%m/%Y')} — {(datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')}")
    if not dataFrame_generation_forecast.empty:    # Ensures that the forecasting DataFrame contains data before attempting to plot
        fig_generation_forecast = px.line(dataFrame_generation_forecast, labels={'value': 'MW', 'index': 'Time'})
        fig_generation_forecast.update_layout(xaxis_title="Time", yaxis_title="Power (MW)", margin=dict(t=50, b=10, l=10, r=10), showlegend=False, height=300)
        st.plotly_chart(fig_generation_forecast, use_container_width=True)
    else:
        st.warning("No generation forecast data available for the next 24 hours.")    # Message-warning in case of data unavailability


    st.markdown("-----")


    # Consumption forecast
    st.markdown("### Consumption Forecast for the next 24 Hours", help="ENTSO-E predictions for total electricity demand (load) for the upcoming day.")
    st.caption(f"Forecast period: {datetime.now().strftime('%d/%m/%Y')} — {(datetime.now() + timedelta(days=1)).strftime('%d/%m/%Y')}")
    if not dataFrame_consumption_forecast.empty:
        fig_consumption_forecast = px.line(dataFrame_consumption_forecast, labels={'value': 'MW', 'index': 'Time'})
        fig_consumption_forecast.update_layout(xaxis_title="Time", yaxis_title="Consumption (MW)", margin=dict(t=50, b=10, l=10, r=10), showlegend=False, height=300)
        st.plotly_chart(fig_consumption_forecast, use_container_width=True)
    else:
        st.warning("No consumption forecast data available for the next 24 hours.")