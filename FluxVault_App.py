import numpy as np  # np mean, np random
import pandas as pd  # read csv, df manipulation
import plotly.express as px  # interactive charts
import streamlit as st 
import plotly.figure_factory as ff
import matplotlib.pyplot as plt

import plotly.graph_objs as go

# For testing
import random 

# STK library imports
from agi.stk12.stkdesktop import STKDesktop
from agi.stk12.stkobjects import *
from agi.stk12.stkutil import *
from agi.stk12.vgt import *

# Comms library
import serial
import struct
import time

st.set_page_config(
    page_title="Flux Vault: Real-Time Dashboard",
    page_icon="🧲",
    layout="wide",
)

@st.cache_data
def stk_mag_generator(sma, ecc, inc, raan, aop, ta):
    # Create a new instance of STK12. Optional arguments set the application visible state and the user-control (whether the application remains open after exiting python.
    stk = STKDesktop.StartApplication(visible=True, userControl=False)
    root = stk.Root
    
    # Create a new scenario.
    root.NewScenario("CapstoneTest")
    scenario = root.CurrentScenario
    scenario.SetTimePeriod("1 Jan 2023 12:00:00", "1 Jan 2023 13:30:00")
    
    # Add a target satellite to the scenario.
    FluxVault_sat = AgSatellite(scenario.Children.New(AgESTKObjectType.eSatellite,"Flux_Sat"))
    FluxVault_sat.SetPropagatorType(7)
    propagator = FluxVault_sat.Propagator 

    # Assign the orbital elements to the satellite's initial state
    propagator.InitialState.Representation.AssignClassical(AgECoordinateSystem.eCoordinateSystemJ2000, sma, ecc, inc, raan, aop, ta)
    
    propagator.Propagate()

    # Reset the animation time to the newly established start time.
    root.Rewind()

    root.UnitPreferences.Item('MagneticField').SetCurrentUnit('Gauss')
    
    elems = [['Time'], ['B Field - Body x'], ['B Field - Body y'], ['B Field - Body z']]
    satDP = FluxVault_sat.DataProviders.Item('SEET Magnetic Field').ExecElements(scenario.StartTime, scenario.StopTime, 60, elems)

    Time = satDP.DataSets.Item(0).GetValues()
    Mag_x = satDP.DataSets.Item(1).GetValues()
    Mag_y = satDP.DataSets.Item(2).GetValues()
    Mag_z = satDP.DataSets.Item(3).GetValues()
    
    mag_field_comp = pd.DataFrame({'Time': Time,
                               'Mag X': Mag_x,
                               'Mag Y': Mag_y,
                               'Mag Z': Mag_z})
    
    del stk

    return mag_field_comp

def create_packet(flag, value, ser):
    packet = start_flag + flag + struct.pack('<f', value) + stop_flag
    ser.write(packet)
    time.sleep(0.1)

def receive_data(ser):
    while ser.read() != start_flag:
        pass
    identifier = ser.read()
    data_bytes = ser.read(4)
    if ser.read() == stop_flag:
        data = struct.unpack('<f', data_bytes)[0]
        return identifier, data
    return None, None

def create_empty_plot(title):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=[], y=[]))
    fig.update_layout(xaxis=dict(title='Time'), yaxis=dict(title='Magnetic Field (uT)'), margin=dict(l=20, r=20, t=40, b=20))
    # fig.update_xaxes(title_text="xaxis 1 title", row=1, col=1)
    return fig

def update_plot_st(x_values, y_values, z_values, measured_x_values, measured_y_values, measured_z_values):
      
    fig_x = go.Figure()
    fig_x.add_trace(go.Scatter(y=x_values, mode='lines', name='X-Value Set Point'))
    fig_x.add_trace(go.Scatter(y=measured_x_values, mode='lines', name='Measured Cage X-Value'))
    fig_x.update_layout(xaxis=dict(title='Time'), yaxis=dict(title='Magnetic Field (uT)'), margin=dict(l=20, r=20, t=20, b=20), showlegend=True)
    plot_x.plotly_chart(fig_x, use_container_width=True)

    # Update the Y component plot and metric
    fig_y = go.Figure()
    fig_y.add_trace(go.Scatter(y=y_values, mode='lines', name='Y-Value Set Point'))
    fig_y.add_trace(go.Scatter(y=measured_y_values, mode='lines', name='Measured Cage Y-Value'))
    fig_y.update_layout(xaxis=dict(title='Time'), yaxis=dict(title='Magnetic Field (uT)'), margin=dict(l=20, r=20, t=20, b=20), showlegend=True)
    plot_y.plotly_chart(fig_y, use_container_width=True)

    # Update the Z component plot and metric
    fig_z = go.Figure()
    fig_z.add_trace(go.Scatter(y=z_values, mode='lines', name='Z-Value Set Point'))
    fig_z.add_trace(go.Scatter(y=measured_z_values, mode='lines', name='Measured Cage Z-Value'))
    fig_z.update_layout(xaxis=dict(title='Time'), yaxis=dict(title='Magnetic Field (uT)'), margin=dict(l=20, r=20, t=20, b=20), showlegend=True)
    plot_z.plotly_chart(fig_z, use_container_width=True)

def run_serial(df):
    # Serial port setup
    serial_port = 'COM7'  
    ser = serial.Serial(serial_port, 115200, timeout=1)
    
    offset = random.uniform(-0.3, 0.3)
    
    # Identifiers 
    x_flag = b'\x00'
    y_flag = b'\x01'
    z_flag = b'\x02'
    
    # Initialize lists to store the data
    x_values, y_values, z_values = [], [], []
    measured_x_values, measured_y_values, measured_z_values = [], [], []
    
    try:
        # while True:
        for index, row in df.iterrows():
            # Extract X, Y, Z values from the DataFrame row
            x, y, z = row['Mag X'], row['Mag Y'], row['Mag Z']
            # x = x_data
            # y = y_data
            # z = z_data
            
            # For testing
            offset = random.uniform(-0.15, 0.15)

            # Send each component and receive the echoed data
            for flag, component in [(x_flag, x), (y_flag, y), (z_flag, z)]:
                create_packet(flag, component, ser)
                id, echoed_data = receive_data(ser)
                if id is not None:
                    if id == x_flag:
                        x_values.append(echoed_data)
                        measured_x_values.append(echoed_data - offset)
                    elif id == y_flag:
                        y_values.append(echoed_data)
                        measured_y_values.append(echoed_data - offset)
                    elif id == z_flag:
                        z_values.append(echoed_data)
                        measured_z_values.append(echoed_data - offset)
                else:
                    st.write('Invalid or incomplete data received')
        
            # Update the metrics on the dashboard with the latest values
            x_metric.metric(label="X-Component (Gauss)", value=x_values[-1] if x_values else 0, delta=x-x_values[-1])
            y_metric.metric(label="Y-Component (Gauss)", value=y_values[-1] if y_values else 0, delta=y-y_values[-1]) 
            z_metric.metric(label="Z-Component (Gauss)", value=z_values[-1] if z_values else 0, delta=z-z_values[-1])
            
            update_plot_st(x_values, y_values, z_values, measured_x_values, measured_y_values, measured_z_values)

            time.sleep(1)  # Adjust the delay as needed

    except KeyboardInterrupt:
        st.write("Stopped by User")
    finally:
        ser.close()

def run_serial_demo2():
    # Serial port setup
    serial_port = 'COM7'  
    ser = serial.Serial(serial_port, 115200, timeout=1)
    
    # Identifiers 
    x_flag = b'\x00'
    y_flag = b'\x01'
    z_flag = b'\x02'
    
    measured_x_values, measured_y_values, measured_z_values = [], [], []
    
    try:
        while True: 
             # Receive the data
            id, data = receive_data(ser)
            if id is not None:
                if id == x_flag:
                    # x_values.append(echoed_data)
                    measured_x_values.append(data)
                elif id == y_flag:
                    # y_values.append(echoed_data)
                    measured_y_values.append(data)
                elif id == z_flag:
                    # z_values.append(echoed_data)
                    measured_z_values.append(data)
            else:
                st.write('Invalid or incomplete data received')
        
            # Update the metrics on the dashboard with the latest values
            x_metric.metric(label="X-Component (Gauss)", value=measured_x_values[-1] if measured_x_values else 0, delta=0)
            y_metric.metric(label="Y-Component (Gauss)", value=measured_y_values[-1] if measured_y_values else 0, delta=0) 
            z_metric.metric(label="Z-Component (Gauss)", value=measured_z_values[-1] if measured_z_values else 0, delta=0)
            
            update_plot_st(measured_x_values, measured_y_values, measured_z_values, measured_x_values, measured_y_values, measured_z_values)

            time.sleep(1)  # Adjust the delay as needed
            
    except KeyboardInterrupt:
        st.write("Stopped by User")
    finally:
        ser.close()

if 'mag_field_comp' not in st.session_state:
    mag_field_comp = pd.DataFrame({'Time':[0,1],
                               'Mag X':[0,1],
                               'Mag Y':[0,1],
                               'Mag Z':[0,1]})
    st.session_state.mag_field_comp = mag_field_comp

# Sidebar for navigation
st.sidebar.title("Navigation")

# creating a single-element container
placeholder = st.empty()

# Home button
home_clicked = st.sidebar.button("Home")

# Page selection
options = ["Home Page", "Flux Vault Comms & Data Viewer", "Flux Vault Team", "Page 3"]
selected_option = st.sidebar.selectbox("Go to", options, index=0)

# Display logic
if home_clicked or selected_option == 'Home Page':
    st.title("Flux Vault Real-Time Overview")
    
    #region STK Input Widgets
    sma_col, ecc_col, inc_col = st.columns(3)
    with sma_col:
        sma = st.number_input("Semi-Major Axis", value = None, placeholder="Enter SMA...")
        st.write('The SMA is:', sma)
    
    with ecc_col:
        ecc = st.number_input("Eccentricity", value=None, placeholder="Enter eccentricity...")
        
    with inc_col:
        inc = st.number_input("Inclination", value=None, placeholder="Enter inclination...")
        
    raan_col, aop_col, ta_col = st.columns(3)
    with raan_col:
        raan = st.number_input("Right Ascension of Ascending Node", value = None, placeholder="Enter RAAN...")
        st.write('The RAAN is', raan)
    
    with aop_col:
        aop = st.number_input("Argument of Perigee", value=None, placeholder="Enter AOP...")
        
    with ta_col:
        ta = st.number_input("True Anomaly", value=None, placeholder="Enter TA...")
    
    #endregion
    
    # Create three columns
    mag_fieldbutton1, mag_fieldbutton_col, mag_fieldbutton3 = st.columns(3)
    
    # Place the button in the middle column
    with mag_fieldbutton_col:
        mag_button_clicked = st.button('Generate Magnetic Field Set-points')
        
    if mag_button_clicked:
        mag_field_comp = stk_mag_generator(sma, ecc, inc, raan, aop, ta)
        st.session_state.mag_field_comp = mag_field_comp
        
    try:
        with st.expander("See Generated Magnetic Field Set-Points"):
            st.dataframe(st.session_state.mag_field_comp, use_container_width=True)
    except NameError:
        st.write('No Dataframe yet')
        
elif selected_option == 'Flux Vault Comms & Data Viewer':
    
    st.title("Flux Vault Data Viewer")

    # Byte definitions
    start_flag = b'\xde'
    stop_flag = b'\xad'
    
    comms_container = st.empty()
    
    read_container = st.empty()
    
    st.header('Magnetic Field Set-Points', divider='rainbow')
    
    # Initialize the metrics in a container
    metrics_container = st.container()
    col1, col2, col3 = metrics_container.columns(3)
    x_metric = col1.metric(label="X-Component (Gauss)", value=0, delta=10)
    y_metric = col2.metric(label="Y-Component (Gauss)", value=0, delta=-10)
    z_metric = col3.metric(label="Z-Component (Gauss)", value=0, delta=10)
               
    st.header('Magnetic Field Profiles', divider='rainbow')
                    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader('X-Component')
        plot_x = st.plotly_chart(create_empty_plot('X Component'), use_container_width=True)
    with col2:
        st.subheader('Y-Component')
        plot_y = st.plotly_chart(create_empty_plot('Y Component'), use_container_width=True)
    with col3:
        st.subheader('Z-Component')
        plot_z = st.plotly_chart(create_empty_plot('Z Component'), use_container_width=True)

    if comms_container.button('Start Communication'):
        run_serial(st.session_state.mag_field_comp)
        
    if read_container.button('Receive Data'):
        run_serial_demo2()
    
elif selected_option == 'Flux Vault Team':
    st.title("Flux Vault Team")
    # Page 2 content goes here
elif selected_option == 'Page 3':
    st.title("Page 3")
    # Page 3 content goes here


