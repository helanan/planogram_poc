import os
import streamlit as st
from supabase import create_client
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 1. Connect to Supabase (reads from environment or Streamlit secrets)
url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")

if not url or not key:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY. Set them as environment variables or in .streamlit/secrets.toml")
    st.stop()

supabase = create_client(url, key)

st.title("🚜 Tractor Supply Planogram POC")

# 2. Pull the data
response = supabase.table("shelf_layout").select("*, products(*)").execute()
data = response.data

if not data:
    st.warning("No shelf layout data found. Make sure the `shelf_layout` and `products` tables are populated.")
    st.stop()

# 3. Build the visualization
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_xlim(0, 48)   # 4-foot shelf section (inches)
ax.set_ylim(0, 36)
ax.set_xlabel("Width (inches)")
ax.set_ylabel("Height (inches)")
ax.set_title("Shelf Layout")

for item in data:
    p = item["products"]
    rect = patches.Rectangle(
        (item["x_pos"], item["y_pos"]),
        p["width_in"],
        p["height_in"],
        edgecolor="black",
        facecolor="#FF5F00",  # TSC Orange
        alpha=0.6,
    )
    ax.add_patch(rect)
    ax.text(
        item["x_pos"] + p["width_in"] / 2,
        item["y_pos"] + p["height_in"] / 2,
        p["name"],
        ha="center",
        va="center",
        fontsize=7,
        wrap=True,
    )
    st.write(f"Placed **{p['name']}** at x={item['x_pos']}\", y={item['y_pos']}\"")

st.pyplot(fig)
