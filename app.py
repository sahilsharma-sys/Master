# FULL FINAL STREAMLIT SCRIPT: Unified Logistics Dashboard ✅

import streamlit as st
import pandas as pd
import requests
import re
from math import radians, sin, cos, sqrt, atan2
import concurrent.futures
import io
from datetime import datetime
import plotly.express as px
import zipfile


st.set_page_config(page_title="📦 Unified Logistics Dashboard", layout="wide", page_icon="📦")

# 🎨 Enhanced Theme Styling
st.markdown("""
    <style>
    /* 🏭 Background warehouse image */
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1581092795360-6fcb9a16c244?auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }

    /* 🔳 Content card style */
    .block-container {
        background-color: rgba(255, 255, 255, 0.93);
        padding: 2.5rem;
        border-radius: 18px;
        margin: 2rem auto;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
    }

    /* 📘 Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #0d47a1 !important;
        color: white !important;
    }

    section[data-testid="stSidebar"] * {
        color: white !important;
        font-weight: 600;
        font-size: 15px;
    }

    /* 📊 Heading and metric text */
    h1, h2, h3 {
        color: #0d47a1 !important;
    }

    .stMetric label {
        color: #0d47a1 !important;
        font-size: 16px;
    }

    /* 🔘 Radio buttons */
    div[role="radiogroup"] > label {
        margin-bottom: 4px;
    }
    </style>
""", unsafe_allow_html=True)


st.markdown("<h1>📦 Logistics Dashboard</h1>", unsafe_allow_html=True)

# ---------------------- Sidebar ----------------------
st.sidebar.title("🧭 Masters")
selection = st.sidebar.radio("Choose a Tool", [
    "🏠 Home",
    "📁 Files Compiler",
    "📂 Files Splitter",
    "🚚 Courier Serviceability",
    "📍 Pincode Zone + Distance",
    "📊 Data Analyzer",
    "🏙️ Zone Only Finder"
])

# ---------------------- Load MIS ----------------------
@st.cache_data
def load_mis():
    file_path = r"D:\Tools\Master File\MIS.xlsb"
    df = pd.read_excel(file_path, sheet_name=0)
    df.columns = df.columns.str.strip()
    return df

# ---------------------- Utilities ----------------------
METRO_RANGES = [
    range(110001, 110099), range(400001, 400105), range(700001, 700105),
    range(600001, 600119), range(560001, 560108), range(500001, 500099),
    range(380001, 380062), range(411001, 411063), range(122001, 122019)
]

def is_metro(pin): return any(int(pin) in r for r in METRO_RANGES)

def get_location(pin):
    headers = {'User-Agent': 'Mozilla/5.0'}

    def try_india_post():
        try:
            res = requests.get(f"https://api.postalpincode.in/pincode/{pin}", timeout=10, headers=headers)
            if res.status_code == 200:
                data = res.json()
                if data and data[0].get("Status", "").lower() == "success":
                    po = data[0].get("PostOffice", [])
                    if po and isinstance(po, list):
                        loc = po[0]
                        return loc.get("Name", ""), loc.get("District", ""), loc.get("State", "")
        except: pass
        return "", "", ""

    def try_worldpostal():
        try:
            res = requests.get(f"https://api.worldpostallocations.com/pincode?postalcode={pin}&countrycode=IN", timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get("status") == "success" and data.get("result"):
                    loc = data["result"][0]
                    return loc.get("place", ""), loc.get("district", ""), loc.get("state", "")
        except: pass
        return "", "", ""

    # Try APIs in order
    for api_call in [try_india_post, try_worldpostal, try_india_post]:
        name, district, state = api_call()
        if all([name, district, state]):
            return name.strip(), district.strip(), state.strip()

    return "Unknown", "Unknown", "Unknown"



def get_latlon(pin):
    try:
        url = f"https://nominatim.openstreetmap.org/search?postalcode={pin}&country=India&format=json"
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = res.json()
        if data: return float(data[0]['lat']), float(data[0]['lon'])
    except: pass
    return None, None

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1-a)), 2)

def classify_zone(fpin, tpin, fd, fs, td, ts):
    special = {"himachal pradesh", "karnataka", "jammu & kashmir", "west bengal", "assam",
               "manipur", "mizoram", "nagaland", "tripura", "meghalaya", "sikkim", "arunachal pradesh"}
    if fpin == tpin: return "LOCAL"
    if fd.lower() == td.lower() and fd != "N/A": return "LOCAL"
    if is_metro(fpin) and is_metro(tpin): return "METRO"
    if fs.lower() == ts.lower(): return "REGIONAL"
    if fs.lower() in special or ts.lower() in special: return "SPECIAL"
    return "ROI"

def process(row):
    f, t = str(row['from_pincode']), str(row['to_pincode'])
    fc, fd, fs = get_location(f)
    tc, td, ts = get_location(t)
    lat1, lon1 = get_latlon(f)
    lat2, lon2 = get_latlon(t)
    dist = haversine(lat1, lon1, lat2, lon2) if None not in [lat1, lon1, lat2, lon2] else "N/A"
    zone = classify_zone(f, t, fd, fs, td, ts)
    return {
        "From": f, "To": t,
        "From City": fc, "From State": fs,
        "To City": tc, "To State": ts,
        "Distance (KM)": dist,
        "Zone": zone
    }

# ---------------------- 🏠 HOME Dashboard ----------------------
if selection == "🏠 Home":
    st.header("📈 Dashboard Overview")
    try:
        mis_df = load_mis()
        created_col = next((c for c in mis_df.columns if "created" in c.lower()), None)
        if created_col:
            mis_df[created_col] = pd.to_datetime(mis_df[created_col], dayfirst=True, errors="coerce")

        order_type = st.selectbox("📌 Filter by Order Type", ["All"] + sorted(mis_df['Order Type'].dropna().unique().tolist()))
        filtered_df = mis_df.copy()
        if order_type != "All":
            filtered_df = filtered_df[filtered_df["Order Type"] == order_type]

        first_col = filtered_df.columns[0]
        mtd_orders = filtered_df[filtered_df[first_col].astype(str).str.strip() != ""].shape[0]
        active_clients = filtered_df['Merchant Name'].nunique()

        cod_count = prepaid_count = 0
        if "Payment Mode" in filtered_df.columns:
            filtered_df["Payment Mode"] = filtered_df["Payment Mode"].astype(str).str.upper()
            cod_count = int(filtered_df["Payment Mode"].str.count("COD").sum())
            prepaid_count = int(filtered_df["Payment Mode"].str.count("PREPAID").sum())

        col1, col2, col3 = st.columns([1, 1, 2])
        col1.metric("📅 MTD Orders", f"{mtd_orders:,}")
        col2.metric("👥 Active Clients", f"{active_clients:,}")
        with col3:
            st.markdown("#### 💳 Payment Mode")
            st.markdown(f"<h5 style='color:#1f77b4;'>{cod_count:,} COD | {prepaid_count:,} Prepaid</h5>", unsafe_allow_html=True)

        st.markdown("### 📊 Insights Overview")
        c1, c2, c3 = st.columns([1, 15, 1])
        with c2:
            top_clients_df = filtered_df["Merchant Name"].value_counts().head(10).reset_index()
            top_clients_df.columns = ["Merchant Name", "Orders"]
            fig1 = px.bar(
                top_clients_df, y="Merchant Name", x="Orders", text="Orders",
                orientation="h", color="Orders", color_continuous_scale="Blues",
                title="🏆 Top 10 Clients by MTD Order Volume"
            )
            fig1.update_layout(xaxis_title="Orders", yaxis_title="Client", plot_bgcolor="white", height=400, title_x=0.2)
            fig1.update_traces(textposition='outside')
            st.plotly_chart(fig1, use_container_width=True)

    except Exception as e:
        st.warning(f"⚠️ Could not load MIS data: {e}")

# 🔁 All other tool sections continue unchanged from your current code...


# ---------------------- Tools Continue Below... ----------------------
# ➤ Your tool sections (Files Compiler, Courier Serviceability, Zone + Distance, etc.)
# ➤ Paste them below this block as you already have


# ---------------------- 📁 Files Compiler ----------------------
if selection == "📁 Files Compiler":
    st.header("📁 Files Compiler")
    files = st.file_uploader("Upload Excel/CSV", type=["xlsx","csv"], accept_multiple_files=True)
    if files:
        dfs = []
        for f in files:
            df0 = pd.read_csv(f) if f.name.endswith(".csv") else pd.read_excel(f)
            df0["Source File"] = f.name
            dfs.append(df0)
        if dfs:
            df_all = pd.concat(dfs, ignore_index=True).fillna("")
            st.dataframe(df_all, use_container_width=True)
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as w: df_all.to_excel(w, index=False)
            st.download_button("⬇️ Download", buf.getvalue(), "compiled.xlsx")

# ---------------------- 📂 Files Splitter ----------------------
elif selection == "📂 Files Splitter":
    st.header("📂 Files Splitter")
    uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx", "csv"])
    if uploaded_file:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.write("### Preview of Uploaded File")
        st.dataframe(df.head(), use_container_width=True)

        col_to_split = st.selectbox("Select column to split by", df.columns)
        output_mode = st.radio("Choose Output Format", ["Single Excel (Multiple Sheets)", "Multiple Excel Files (ZIP)"])

        if col_to_split:
            unique_vals = df[col_to_split].dropna().unique().tolist()
            st.write(f"Found {len(unique_vals)} unique values in '{col_to_split}'")

            if output_mode == "Single Excel (Multiple Sheets)":
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                    for val in unique_vals:
                        df_val = df[df[col_to_split] == val]
                        sheet_name = str(val)[:31]
                        df_val.to_excel(writer, sheet_name=sheet_name, index=False)
                st.download_button("⬇️ Download Split Excel", buffer.getvalue(), file_name="split_output.xlsx")

            else:  # Multiple Excel Files in ZIP
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for val in unique_vals:
                        df_val = df[df[col_to_split] == val]
                        excel_bytes = io.BytesIO()
                        with pd.ExcelWriter(excel_bytes, engine="xlsxwriter") as writer:
                            df_val.to_excel(writer, index=False)
                        zip_file.writestr(f"{val}.xlsx", excel_bytes.getvalue())
                st.download_button("⬇️ Download ZIP of Files", zip_buffer.getvalue(), file_name="split_files.zip")


elif selection == "🚚 Courier Serviceability":
    st.header("🚚 Courier Serviceability")
    path_forward = r"D:\Sahil\Servicebility\Pincode servicability Master Updated 19-Nov-2024.xlsb"
    path_reverse = r"D:\Sahil\Servicebility\Pincode servicability Master Updated 19-Nov-2024.xlsb"

    # ✅ Robust Loader Function
    @st.cache_data
    def load_serviceability(sheet_name):
        raw = pd.read_excel(path_forward, sheet_name=sheet_name, engine="pyxlsb", header=None)
        raw = raw.dropna(how='all')  # Drop empty rows
        cols = raw.iloc[0].fillna("").astype(str).str.strip()
        df0 = raw[1:].copy()
        df0.columns = cols

        pin_col = next((c for c in df0.columns if "pincode" in c.lower()), df0.columns[1])
        df0.rename(columns={pin_col: "Pincode"}, inplace=True)
        df0["Pincode"] = df0["Pincode"].astype(str).str.extract(r'(\d{6})')[0].fillna("").str.zfill(6)
        return df0

    # ✅ Toggle Forward/Reverse
    service_type = st.radio("Select Type", ["Forward", "Reverse"])
    sheet_name = "Sheet1" if service_type == "Forward" else "RVP Serviceability"
    master_df = load_serviceability(sheet_name)

    mode = st.radio("Mode", ["🔍 Manual", "📤 Upload CSV"])
    filt = st.selectbox("Filter", ["Both","Prepaid","COD"])

    def badge(items, color):
        return " ".join([
            f"<span style='background-color:{color};color:white;padding:3px 7px;border-radius:4px;margin:1px'>{i}</span>"
            for i in items
        ])

    def base(col): return re.split(r"[\s_/-]+", (col))[0].title()

    def chk(p):
        r0 = master_df[master_df["Pincode"] == p]
        if r0.empty: return {"Pincode": p, "Serviceable": "❌ Not found", "Non Serviceable": ""}
        y, n = set(), set()
        rd = r0.iloc[0]
        for c in master_df.columns[2:]:
            if filt != "Both" and filt.lower() not in c.lower(): continue
            val = str(rd[c]).strip().upper()
            key = base(c).upper()
            if val == "Y": y.add(key)
            if val == "N": n.add(key)
        return {
            "Pincode": p,
            "Serviceable": badge(sorted(y), "#28a745"),
            "Non Serviceable": badge(sorted(n - y), "#dc3545")
        }

    if mode == "🔍 Manual":
        txt = st.text_area("Enter pincodes, one per line", height=200)
        if txt:
            pins = [x.strip().zfill(6) for x in txt.splitlines() if x.strip()]
            out = [chk(p) for p in pins]
            st.markdown(pd.DataFrame(out).to_html(escape=False, index=False), unsafe_allow_html=True)
    else:
        fl = st.file_uploader("Upload CSV with 'Pincode'", type="csv")
        if fl:
            inp = pd.read_csv(fl)["Pincode"].astype(str).str.zfill(6).tolist()
            out = [chk(p) for p in inp]
            st.markdown(pd.DataFrame(out).to_html(escape=False, index=False), unsafe_allow_html=True)


elif selection == "📍 Pincode Zone + Distance":
    st.header("📍 Pincode To Pincode")
    mode = st.radio("Mode", ["📤 Upload File", "✍️ Manual Pairs"])
    if mode=="📤 Upload File":
        fl=st.file_uploader("Upload with from_pincode,to_pincode",type=["csv","xlsx"])
        if fl:
            df0 = pd.read_csv(fl) if fl.name.endswith(".csv") else pd.read_excel(fl)
            if 'from_pincode' in df0.columns and 'to_pincode' in df0.columns:
                with concurrent.futures.ThreadPoolExecutor() as ex:
                    out=[process(r) for r in df0.to_dict("records")]
                dfRes=pd.DataFrame(out); st.dataframe(dfRes, use_container_width=True)
                st.download_button("⬇️ Download CSV", dfRes.to_csv(index=False).encode(), "zones.csv")
    else:
        txt=st.text_area("Enter pairs as 'from,to' per line",height=200)
        if txt:
            pairs=[line.split(",") for line in txt.splitlines() if "," in line]
            df_pairs=pd.DataFrame(pairs,columns=["from_pincode","to_pincode"])
            with concurrent.futures.ThreadPoolExecutor() as ex:
                out=[process(r) for r in df_pairs.to_dict("records")]
            st.dataframe(pd.DataFrame(out), use_container_width=True)

elif selection == "📊 Data Analyzer":
    st.header("📊 Data Analyzer")
    fl=st.file_uploader("Upload CSV or Excel",type=["csv","xlsx"])
    if fl:
        df0=pd.read_csv(fl) if fl.name.endswith(".csv") else pd.read_excel(fl)
        cols=list(df0.columns)
        st.sidebar.header("🧩 Map Columns")
        s=st.sidebar.selectbox("Status",["--None--"]+cols)
        cl=st.sidebar.selectbox("Client",["--None--"]+cols)
        cr=st.sidebar.selectbox("Courier",["--None--"]+cols)
        dt=st.sidebar.selectbox("Date",["--None--"]+cols)
        st.dataframe(df0, use_container_width=True)

elif selection == "🏙️ Zone Only Finder":
    st.header("🏙️ Zone Only")
    f = st.text_input("From Pincode")
    t = st.text_input("To Pincode")
    if st.button("🔍 Check"):
        fc, fd, fs = get_location(f)
        tc, td, ts = get_location(t)
        zone = classify_zone(f, t, fd, fs, td, ts)
        st.success(f"📍 Zone: **{zone}**")

