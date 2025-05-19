import streamlit as st
import pandas as pd
import sqlite3
import snap7
import base64
import struct
import time
import streamlit_autorefresh
import datetime
from PIL import Image

icon = Image.open("dreamz.png")

st.set_page_config(layout="wide", page_title="Cold Room Dashboard", page_icon=icon)
# Refresh timers
streamlit_autorefresh.st_autorefresh(interval=10_000, key="refresh")
refresh_count = streamlit_autorefresh.st_autorefresh(interval=5000, key="door_status_refresh")

# Encode your image in base64
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode()
    return encoded

# Get base64 image string
logo_base64 = get_base64_image("logo.png")

# Inject HTML with CSS to position logo at top right
st.markdown(f"""
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h1 style="color: #1E90FF;">Cold Room Dashboard</h1>
        <img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="height:60px;" />
    </div>
    <hr style="margin-top: 10px;">
""", unsafe_allow_html=True)



# PLC Connection
client = snap7.client.Client()
client.connect("192.168.100.120", 0, 1)

# Helpers
def read_bit(db_num, start, bit):
    try:
        data = client.db_read(db_num, start, 1)
        return (data[0] >> bit) & 1
    except Exception as e:
        st.error(f"Error reading bit from DB{db_num} start {start} bit {bit}: {e}")
        return None

def read_real(db_num, start):
    data = client.db_read(db_num, start, 4)
    return struct.unpack('>f', data)[0]

def Read_Temp_Set(db_num, start):
    data = client.db_read(db_num, start, 4)
    return struct.unpack('>f', data)[0]

def load_data():
    conn = sqlite3.connect("data_log.db")
    query = "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 500"
    return pd.read_sql_query(query, conn)

# Layout split
left_col, right_col = st.columns([1, 2])

# ----- LEFT COLUMN: Door Status -----
with left_col:
    #st.subheader("Live Door Status")

    st.markdown("""
    <h1 style='text-align: center;font-size:28px; color: #cf04ad;'>
        Live Door Status
    </h1>
""", unsafe_allow_html=True)

    door_names = ["Cold Room 1 Door", "Cold Room 2 Door", "Cold Room 3 Door", "Cold Room 4 Door", "Cold Room 5 Door"]
    blink_on = (refresh_count % 2) == 0

    for i, door_name in enumerate(door_names):
        status = read_bit(25, 0, i) # read_bits(db_num, start, bit) where start = byteoffset, bit = i

        if status is None:
         display_text = "Error"
         symbol = "    🚪"
         color = "#888888"
        elif status == 1:
         display_text = "OPEN 🔴"
         symbol = "    🚪🔓"
         color = "#000000"
         bg1 = "#4d434345"
        else:
         display_text = "Closed 🟢"
         symbol = "    🚪🔒"
         color = "#000000"
         bg1 = "#4d434345"

        html = f"""
        <div style='padding:0px; border:0px solid #311; border-radius:8px;margin-left:90px;margin-right:140px; margin-bottom:5px; background-color:{bg1} ; background-color:{bg1}'>
        <h4 style='text-align: center;margin-bottom:5px; border:0px solid #311;color:{color}; font-size:20px;'>{symbol} {door_name}</h4>
        <p style='text-align: center;font-size:24px; font-weight:bold; color:{color};horizintal-alignment:center; margin:5px 0 0;'>{display_text}</p>
        </div>
      """
        st.markdown(html, unsafe_allow_html=True)

# ----- RIGHT COLUMN: Temperatures + Trends -----
with right_col:
    #st.subheader("Live Temperatures")
    st.markdown("""
    <h1 style='text-align: center;font-size:28px; color: #cf04ad;'>
        Live Temperatures
    </h1>
    """, unsafe_allow_html=True)
    # Read temperatures from PLC
    temp_cols = st.columns(5)
    for i in range(5):
        temp = read_real(24, i * 4)  # read_real(db_num, start) where start = i * 4
        Set_temp = Read_Temp_Set(36, i * 4) 
        if temp > Set_temp :
            bg_color = "#ff4d4d"  # red
            fg_color = "#FFFFFF"
        elif temp > Set_temp - 2:
            bg_color = "#ffff66"  # yellow
            fg_color = "#000000"
        else:
            bg_color = "#85e085"  # green
            fg_color = "#000000"

        temp_html = f"""
            <div style='background-color: {bg_color}; color: {fg_color};padding: 0px; border-radius: 10px; text-align: center'>
                <h4 style='text-align: center;margin: 0;'>Temperature {i+1}</h4>
                <p style='text-align: center;font-size: 24px; margin: 0;'><strong>{temp:.2f} °C</strong></p>
            </div>
        """

        temp_cols[i].markdown(temp_html, unsafe_allow_html=True)


        #temp_cols[i].metric(f"Temperature {i+1}", f"{temp:.2f} \u00B0C", border=True)

    # --- Historical Trends ---
    #st.subheader("Temperature Trends")
    st.markdown("""
    <h1 style='text-align: center;font-size:28px; color: #cf04ad;'>
        Temperature Trends
    </h1>
""", unsafe_allow_html=True)

    # Add start/end date filtering
    import datetime
    sel_Date_time=st.columns(2)
    start_dt = st.date_input("Start date", value=datetime.date.today() - datetime.timedelta(days=1))
    end_dt = st.date_input("End date", value=datetime.date.today())
   # sel_Date_time[2].metric(border=True)
    data = load_data()

    if data.empty:
        st.warning("No data found in logs table.")
    else:
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        filtered_data = data[(data['timestamp'].dt.date >= start_dt) & (data['timestamp'].dt.date <= end_dt)]

        if filtered_data.empty:
            st.warning("No data in selected date range.")
        else:
            pivoted = filtered_data.pivot(index="timestamp", columns="name", values="value")
            pivoted.index = pd.to_datetime(pivoted.index)

            analog_tags = [tag for tag in pivoted.columns if "Door" not in tag]
            selected = st.multiselect("Select analog tags", options=analog_tags, default=["Temperature1"])

            if selected:
                st.line_chart(pivoted[selected])
            else:
                st.info("Select one or more analog tags to display the trend chart.")
