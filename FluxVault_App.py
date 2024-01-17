import numpy as np  # np mean, np random
import pandas as pd  # read csv, df manipulation
import plotly.express as px  # interactive charts
import streamlit as st 

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
    page_icon="🧭",
    layout="wide",
)

def stk_mag_generator(sma, ecc, inc, raan, aop, ta):
    # Create a new instance of STK12. Optional arguments set the application visible state and the user-control (whether the application remains open after exiting python.
    stk = STKDesktop.StartApplication(visible=True, userControl=True)
    root = stk.Root
    
    # Create a new scenario.
    root.NewScenario("CapstoneTest")
    scenario = root.CurrentScenario
    scenario.SetTimePeriod("1 Jan 2023 12:00:00", "2 Jan 2023 12:00:00")
    
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

    return mag_field_comp
    
def create_packet(data1, data2, data3):
    start_delimiter = b'\xAA'  # Start delimiter
    end_delimiter = b'\xBB'    # End delimiter
    
    # Convert each float to 4 bytes and concatenate
    data_bytes = struct.pack('fff', data1, data2, data3)  

    packet = start_delimiter + data_bytes + end_delimiter
    return packet

# Sidebar for navigation
st.sidebar.title("Navigation")

# Home button
home_clicked = st.sidebar.button("Home")

# Page selection
options = ["Home Page", "Page 1", "Page 2", "Page 3"]
selected_option = st.sidebar.selectbox("Go to", options, index=0)

# Display logic
if home_clicked or selected_option == 'Home Page':
    st.title("Flux Vault Real-Time Overview")
    
    # Home page content goes here
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
        
    # Create three columns
    mag_fieldbutton1, mag_fieldbutton_col, mag_fieldbutton3 = st.columns(3)

    # Place the button in the middle column
    with mag_fieldbutton_col:
        mag_button_clicked = st.button('Generate Magnetic Field Set-points')
        
    if mag_button_clicked:
        mag_field_comp = stk_mag_generator(sma, ecc, inc, raan, aop, ta)
    
    # try:
    #     if mag_field_comp:
    #         st.dataframe(mag_field_comp)
    # except NameError:
    #     st.write('No Dataframe yet')
    
    st.dataframe(mag_field_comp)
    
    # # Iterating through each row
    # for index, row in mag_field_comp.iterrows():
    #     # Access data in each column
    #     column2_value = row['Mag X']
    #     column3_value = row['Mag Y']
        
    #     st.write(f"Row {index}: Column1 = {column2_value}, Column2 = {column3_value}")
        
    # Serial Comm
    serial_comm_button = st.button('Send Data')
    
    if serial_comm_button:
        ser = serial.Serial('COM3', 9600, timeout=1)

        try:
            while True:
                # Example mag data
                float_data1 = 123.456
                float_data2 = 78.910
                float_data3 = 11.1213

                packet = create_packet(float_data1, float_data2, float_data3)
                ser.write(packet)  # Send the packet
                time.sleep(1)  # Interval between packets
        except KeyboardInterrupt:
            print("Transmission stopped")
        finally:
            ser.close()
        
elif selected_option == 'Page 1':
    st.title("Page 1")
    # Page 1 content goes here
elif selected_option == 'Page 2':
    st.title("Page 2")
    # Page 2 content goes here
elif selected_option == 'Page 3':
    st.title("Page 3")
    # Page 3 content goes here


