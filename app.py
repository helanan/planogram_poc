import os
import streamlit as st
from supabase import create_client
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe
import numpy as np

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Heartland Supply Co. — Planogram", layout="wide")

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #2E5339 0%, #4A7C59 100%);
        padding: 1.2rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: #F5E6C8; margin: 0; font-size: 2rem; }
    .main-header p  { color: #C8DFC8; margin: 0.2rem 0 0; font-size: 0.9rem; }
    .metric-card {
        background: #F8F4EE;
        border-left: 4px solid #2E5339;
        padding: 0.6rem 1rem;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="main-header">
    <h1>🌾 Heartland Supply Co.</h1>
    <p>Planogram Management System</p>
</div>
""", unsafe_allow_html=True)

# ── Supabase connection ────────────────────────────────────────────────────────
url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL", "")
key = os.environ.get("SUPABASE_KEY") or st.secrets.get("SUPABASE_KEY", "")

if not url or not key:
    st.error("Missing SUPABASE_URL or SUPABASE_KEY.")
    st.stop()

supabase = create_client(url, key)

# ── Data ───────────────────────────────────────────────────────────────────────
response = supabase.table("shelf_layout").select("*, products(*)").execute()
data = response.data

if not data:
    st.warning("No shelf layout data found.")
    st.stop()

shelf_baselines = sorted(set(item["y_pos"] for item in data))
n_shelves   = len(shelf_baselines)
shelf_width = 48
shelf_gap   = 18   # vertical space per shelf band

baseline_map = {y: i * shelf_gap for i, y in enumerate(shelf_baselines)}

# ── Metrics row ───────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
col1.metric("Total SKUs", len(data))
col2.metric("Shelves", n_shelves)
total_w = sum(item["products"]["width_in"] for item in data)
col3.metric("Linear Feet Used", f"{total_w / 12:.1f} ft / {shelf_width / 12:.0f} ft")

st.divider()

# ── Colour palette (one per shelf) ────────────────────────────────────────────
SHELF_COLORS = ["#E07B39", "#4A7C59", "#5B8DB8", "#C0392B", "#8E6BBF"]

# ── Figure ────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 3.2 * n_shelves))
fig.patch.set_facecolor("#F8F4EE")
ax.set_facecolor("#F8F4EE")

total_height = n_shelves * shelf_gap
ax.set_xlim(-2, shelf_width + 2)
ax.set_ylim(-1, total_height + 2)
ax.set_aspect("equal")
ax.axis("off")

fig.suptitle("Store Shelf Layout", fontsize=15, fontweight="bold",
             color="#2E5339", y=1.01)

for raw_y, display_y in baseline_map.items():
    shelf_num = list(baseline_map.keys()).index(raw_y)
    color     = SHELF_COLORS[shelf_num % len(SHELF_COLORS)]

    # Shelf back panel
    back = patches.Rectangle(
        (0, display_y), shelf_width, shelf_gap - 1,
        facecolor="#EDE3D3", edgecolor="none", zorder=1, alpha=0.6
    )
    ax.add_patch(back)

    # Shelf board (thick plank at the base)
    board = patches.Rectangle(
        (0, display_y - 1.2), shelf_width, 1.2,
        facecolor="#8B6340", edgecolor="#5C3D1E", linewidth=0.8, zorder=3
    )
    ax.add_patch(board)

    # Side brackets
    for bx in [0, shelf_width]:
        bracket = patches.Rectangle(
            (bx - 0.8 if bx > 0 else bx, display_y - 1.2),
            0.8, shelf_gap,
            facecolor="#6B4C2A", edgecolor="none", zorder=2
        )
        ax.add_patch(bracket)

    # Shelf label
    ax.text(-1.2, display_y + (shelf_gap / 2), f"Shelf {shelf_num + 1}",
            fontsize=8, fontweight="bold", color="#5C3D1E",
            va="center", ha="right", rotation=90)

    # Products on this shelf
    shelf_items = [item for item in data if item["y_pos"] == raw_y]
    for item in shelf_items:
        p = item["products"]
        x, w, h = item["x_pos"], p["width_in"], p["height_in"]

        # Product box with rounded corners
        prod_rect = FancyBboxPatch(
            (x + 0.15, display_y + 0.15), w - 0.3, h - 0.3,
            boxstyle="round,pad=0.1",
            facecolor=color, edgecolor="white",
            linewidth=1.2, alpha=0.88, zorder=4
        )
        ax.add_patch(prod_rect)

        # Subtle top highlight
        highlight = patches.Rectangle(
            (x + 0.3, display_y + h - 1.8), w - 0.6, 1.4,
            facecolor="white", alpha=0.18, zorder=5
        )
        ax.add_patch(highlight)

        # Product name (wrapped manually at ~10 chars)
        words  = p["name"].split()
        lines  = []
        line   = ""
        for word in words:
            if len(line) + len(word) > 10 and line:
                lines.append(line.strip())
                line = word + " "
            else:
                line += word + " "
        if line:
            lines.append(line.strip())
        label = "\n".join(lines)

        ax.text(x + w / 2, display_y + h / 2, label,
                ha="center", va="center", fontsize=6.2,
                color="white", fontweight="bold", zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground="black")])

plt.tight_layout()
st.pyplot(fig, use_container_width=True)

# ── Summary table ─────────────────────────────────────────────────────────────
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
