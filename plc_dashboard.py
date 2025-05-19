import streamlit as st
import pandas as pd
import snap7
import datetime
import base64
import sqlite3
import os
from streamlit_autorefresh import st_autorefresh

# ---------- Configuration ----------
PLC_IP = "192.168.200.16"
DB_TEMP = 24
DB_DOOR = 25
NUM_SENSORS = 5
TEMP_LIMIT = 36
LOG_FILE = "temp_log.csv"
logo_path = "logo.png"

# ---------- PLC Setup ----------
client = snap7.client.Client()
try:
    client.connect(PLC_IP, 0, 1)
except:
    st.error(f"Could not connect to PLC at {PLC_IP}")

# ---------- Helper Functions ----------
def read_real(db_num, start):
    try:
        data = client.db_read(db_num, start, 4)
        return snap7.util.get_real(data, 0)
    except:
        return None

def read_bit(db_num, byte_index, bit_index):
    try:
        data = client.db_read(db_num, byte_index, 1)
        byte_val = int.from_bytes(data, byteorder='big')
        return (byte_val >> bit_index) & 1
    except:
        return None

def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def log_data():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i in range(NUM_SENSORS):
        temp = read_real(DB_TEMP, i * 4)
        if temp is not None:
            name = f"Temperature {i+1}"
            df = pd.DataFrame([[now, name, temp]], columns=["timestamp", "name", "value"])
            df.to_csv(LOG_FILE, mode='a', index=False, header=not os.path.exists(LOG_FILE))

def load_dataLive():
    conn = sqlite3.connect("data_log.db")
    query = "SELECT * FROM logs ORDER BY timestamp DESC LIMIT 500"
    return pd.read_sql_query(query, conn)


def load_data():
    conn = sqlite3.connect("data_log.db")
    query = "SELECT * FROM logs ORDER BY timestamp DESC"
    return pd.read_sql_query(query, conn)

# ---------- Sidebar ----------
with st.sidebar:
    st.title("🚪 Cold Room IOT2050")
    mode = st.radio("Select View Mode", ["Live", "Historical"])
    st.markdown("---")
    st.markdown("Created by **Dreamz Automation System Pvt. Ltd.**")
    st.markdown("📅 " + datetime.datetime.now().strftime("%d %b %Y, %H:%M"))

# ---------- Refresh ----------
if mode == "Live":
    st_autorefresh(interval=5000, key="autorefresh")

# ---------- Header ----------
if os.path.exists(logo_path):
    logo_base64 = get_base64_image(logo_path)
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h1 style="color: #1E90FF;">Cold Room Dashboard - IOT2050</h1>
            <img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="height:60px;" />
        </div>
        <hr style="margin-top: 10px;">
    """, unsafe_allow_html=True)
else:
    st.title("Cold Room Dashboard - IOT2050")

# ---------- LIVE MODE ----------
if mode == "Live":
    left_col, right_col = st.columns([1, 2])

    with left_col:
        st.markdown("<h2 style='text-align:center; color:#cf04ad;'>Live Door Status</h2>", unsafe_allow_html=True)
        door_names = [f"Cold Room {i+1} Door" for i in range(NUM_SENSORS)]
        for i, name in enumerate(door_names):
            status = read_bit(DB_DOOR, 0, i)
            state = "Closed 🟢" if status == 0 else "OPEN 🔴" if status == 1 else "Error"
            color = "#000000" if status == 0 else "#000000" if status == 1 else "#888"
            html = f"""
            <div style='padding:10px; border-radius:8px;margin-bottom:5px; background-color:#f2f2f2;'>
                <h4 style='text-align: center; color: {color};'>{name}</h4>
                <p style='text-align: center; font-size: 24px; font-weight: bold; color: {color};'>{state}</p>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)

    with right_col:
        st.markdown("<h2 style='text-align:center; color:#cf04ad;'>Live Temperatures</h2>", unsafe_allow_html=True)
        temp_cols = st.columns(NUM_SENSORS)
        temp_values = []
        for i in range(NUM_SENSORS):
            temp = read_real(DB_TEMP, i * 4)
            temp_values.append(temp)
            if temp > TEMP_LIMIT:
                bg, fg = "#ff4d4d", "#fff"
            elif temp > 18:
                bg, fg = "#ffff66", "#000"
            else:
                bg, fg = "#85e085", "#000"
            box = f"""
            <div style='background-color: {bg}; color: {fg}; padding: 10px; border-radius: 10px; text-align: center'>
                <h4>Temperature {i+1}</h4>
                <p style='font-size: 24px;'><strong>{temp:.2f} °C</strong></p>
            </div>
            """
            temp_cols[i].markdown(box, unsafe_allow_html=True)

        # ----- Show Live Trend Below -----
          #st.subheader("Temperature Trends")
        st.markdown("""
        <h1 style='text-align: center;font-size:28px; color: #cf04ad;'>
        Temperature Trends
        </h1>
        """, unsafe_allow_html=True)

         # Add start/end date filtering
         #import datetime
    
        start_dt = value=datetime.date.today() - datetime.timedelta(days=1)#st.date_input("Start date", value=datetime.date.today() - datetime.timedelta(days=1))
        end_dt =value=datetime.date.today()# st.date_input("End date", value=datetime.date.today())

        # sel_Date_time[2].metric(border=True)
        data = load_dataLive()

        if data.empty:
         st.warning("No data found in logs table.")
        else:
         data['timestamp'] = pd.to_datetime(data['timestamp'])
         filtered_data = data[(data['timestamp'].dt.date >= start_dt) & (data['timestamp'].dt.date <= end_dt)]
        # filtered_data = data[(data['timestamp'] >= start_dt) & (data['timestamp'] <= end_dt)]

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


    # Optional logging for historical
   # log_data()

# ---------- HISTORICAL MODE ----------
elif mode == "Historical":
     # --- Historical Trends ---
    #st.subheader("Temperature Trends")
    st.markdown("""
    <h1 style='text-align: center;font-size:28px; color: #cf04ad;'>
        Temperature Trends
    </h1>
""", unsafe_allow_html=True)

    # Add start/end date filtering
    #import datetime
    
    #start_dt = st.date_input("Start date", value=datetime.date.today() - datetime.timedelta(days=1))
    #end_dt = st.date_input("End date", value=datetime.date.today())

#     # Date and time input for filtering
    start_date = st.date_input("Start date", value=datetime.date.today() - datetime.timedelta(days=1))
    start_time = st.time_input("Start time", value=datetime.time(0, 0))
    end_date = st.date_input("End date", value=datetime.date.today())
    end_time = st.time_input("End time", value=datetime.time(0, 0))

    # Combine date and time into datetime objects
    start_dt = datetime.datetime.combine(start_date, start_time)
    end_dt = datetime.datetime.combine(end_date, end_time)
# ...existing code...

   # sel_Date_time[2].metric(border=True)
    data = load_data()

    if data.empty:
        st.warning("No data found in logs table.")
    else:
        data['timestamp'] = pd.to_datetime(data['timestamp'])
        #filtered_data = data[(data['timestamp'].dt.date >= start_dt) & (data['timestamp'].dt.date <= end_dt)]
        filtered_data = data[(data['timestamp'] >= start_dt) & (data['timestamp'] <= end_dt)]

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


# ---------- Disconnect ----------
if client.get_connected():
    client.disconnect()
