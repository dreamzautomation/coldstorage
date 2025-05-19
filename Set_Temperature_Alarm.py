import streamlit as st
import base64
import snap7
from snap7.util import get_real, set_real
from PIL import Image

icon = Image.open("dreamz.png")

st.set_page_config(page_title="Set Multiple Temperature Setpoints", layout="wide",page_icon=icon)
#st.header("🌡️ Set Multiple Temperature Setpoints")


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
        <h1 style="color: #1E90FF;">Set Temperature Setpoints</h1>
        <img src="data:image/png;base64,{logo_base64}" alt="Company Logo" style="height:60px;" />
    </div>
    <hr style="margin-top: 10px;">
""", unsafe_allow_html=True)



PLC_IP = "192.168.100.120"
DB_NUMBER = 36
NUM_SETPOINTS = 5

def connect_to_plc(ip, rack=0, slot=1):
    plc = snap7.client.Client()
    try:
        plc.connect(ip, rack, slot)
        if plc.get_connected():
            return plc
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
    return None

def read_setpoints(plc, db_number, count):
    try:
        data = plc.db_read(db_number, 0, count * 4)
        return [get_real(data, i * 4) for i in range(count)]
    except Exception as e:
        st.error(f"❌ Failed to read from PLC: {e}")
        return [0.0] * count

def write_setpoints(plc, db_number, values):
    try:
        for i, val in enumerate(values):
            data = bytearray(4)
            set_real(data, 0, val)
            plc.db_write(db_number, i * 4, data)
        return True
    except Exception as e:
        st.error(f"❌ Failed to write to PLC: {e}")
        return False

plc = connect_to_plc(PLC_IP)
setpoints = read_setpoints(plc, DB_NUMBER, NUM_SETPOINTS) if plc else [0.0] * NUM_SETPOINTS

new_setpoints = []
for i, val in enumerate(setpoints):
    sp = st.number_input(f"Temperature {i+1} Setpoint  (°C)", value=val, format="%.2f", key=f"setpoint_{i}")
    new_setpoints.append(sp)

if st.button("Write All Setpoints to PLC"):
    if plc:
        success = write_setpoints(plc, DB_NUMBER, new_setpoints)
        if success:
            st.success("✅ All setpoints written successfully.")
        else:
            st.error("⚠️ Some values failed to write.")
        plc.disconnect()
    else:
        st.error("🔌 Not connected to PLC.")
