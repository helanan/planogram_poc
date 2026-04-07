import os
import streamlit as st
from supabase import create_client
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 1. Connect to Supabase
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

# 3. Derive shelf baselines from the data (unique y_pos values, sorted)
shelf_baselines = sorted(set(item["y_pos"] for item in data))
shelf_height = 16   # vertical space allocated per shelf (inches)
shelf_width = 48    # total width (inches)

total_height = len(shelf_baselines) * shelf_height

# 4. Build the visualization
fig, ax = plt.subplots(figsize=(12, 2.5 * len(shelf_baselines)))
ax.set_xlim(0, shelf_width)
ax.set_ylim(0, total_height)
ax.set_xlabel("Width (inches)")
ax.set_ylabel("Height (inches)")
ax.set_title("Shelf Layout")
ax.set_aspect("equal")

# Remap each shelf's y_pos to a stacked display position
baseline_map = {y: i * shelf_height for i, y in enumerate(shelf_baselines)}

# Draw shelf baselines and labels
for raw_y, display_y in baseline_map.items():
    ax.axhline(display_y, color="#5C3D1E", linewidth=3, zorder=1)
    ax.text(-1, display_y + 1, f"Shelf {list(baseline_map.keys()).index(raw_y) + 1}",
            fontsize=8, color="#5C3D1E", va="bottom", ha="right")

# Draw products
for item in data:
    p = item["products"]
    display_y = baseline_map[item["y_pos"]]
    rect = patches.Rectangle(
        (item["x_pos"], display_y),
        p["width_in"],
        p["height_in"],
        edgecolor="black",
        facecolor="#FF5F00",  # TSC Orange
        alpha=0.7,
        zorder=2,
    )
    ax.add_patch(rect)
    ax.text(
        item["x_pos"] + p["width_in"] / 2,
        display_y + p["height_in"] / 2,
        p["name"],
        ha="center",
        va="center",
        fontsize=6.5,
        zorder=3,
    )

plt.tight_layout()
st.pyplot(fig)

# 5. Summary table below the diagram
st.subheader("Product Placement")
rows = []
for item in data:
    p = item["products"]
    shelf_num = list(baseline_map.keys()).index(item["y_pos"]) + 1
    rows.append({
        "Shelf": shelf_num,
        "Product": p["name"],
        "SKU": p.get("sku", ""),
        "x (in)": item["x_pos"],
        "W (in)": p["width_in"],
        "H (in)": p["height_in"],
    })
rows.sort(key=lambda r: (r["Shelf"], r["x (in)"]))
st.table(rows)
