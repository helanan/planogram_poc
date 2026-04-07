import os
import streamlit as st
from supabase import create_client
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

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

# ── Raw data ──────────────────────────────────────────────────────────────────
response = supabase.table("shelf_layout").select("*, products(*)").execute()
all_data = response.data

if not all_data:
    st.warning("No shelf layout data found.")
    st.stop()

all_baselines = sorted(set(item["y_pos"] for item in all_data))
shelf_width   = 48
shelf_gap     = 18
SHELF_COLORS  = ["#E07B39", "#4A7C59", "#5B8DB8", "#C0392B", "#8E6BBF"]

# Map raw y_pos → shelf number (1-based), stable across filters
y_to_shelf = {y: i + 1 for i, y in enumerate(all_baselines)}

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters & Sorting")

    shelf_options = [f"Shelf {y_to_shelf[y]}" for y in all_baselines]
    selected_shelves = st.multiselect(
        "Shelves", shelf_options, default=shelf_options
    )
    selected_shelf_nums = {int(s.split()[1]) for s in selected_shelves}

    sku_search = st.text_input("Search by product name or SKU", "")

    st.divider()
    sort_col = st.selectbox(
        "Sort table by",
        ["Shelf", "Product", "SKU", "x (in)", "W (in)", "H (in)"]
    )
    sort_asc = st.radio("Order", ["Ascending", "Descending"]) == "Ascending"

# ── Filter data ───────────────────────────────────────────────────────────────
def matches(item):
    shelf_num = y_to_shelf[item["y_pos"]]
    if shelf_num not in selected_shelf_nums:
        return False
    if sku_search:
        q = sku_search.lower()
        p = item["products"]
        if q not in p["name"].lower() and q not in (p.get("sku") or "").lower():
            return False
    return True

filtered_data = [item for item in all_data if matches(item)]

# ── Metrics (based on filtered set) ───────────────────────────────────────────
col1, col2, col3 = st.columns(3)
filtered_shelves = len(set(item["y_pos"] for item in filtered_data))
total_w = sum(item["products"]["width_in"] for item in filtered_data)
col1.metric("SKUs Shown", f"{len(filtered_data)} / {len(all_data)}")
col2.metric("Shelves Shown", f"{filtered_shelves} / {len(all_baselines)}")
col3.metric("Linear Feet Used", f"{total_w / 12:.1f} ft / {shelf_width / 12:.0f} ft")

st.divider()

if not filtered_data:
    st.info("No products match the current filters.")
    st.stop()

# ── Planogram ─────────────────────────────────────────────────────────────────
# Only show shelves that have at least one visible product; keep original order
visible_baselines = [y for y in all_baselines if y_to_shelf[y] in selected_shelf_nums
                     and any(item["y_pos"] == y for item in filtered_data)]
n_visible  = len(visible_baselines)
baseline_map = {y: i * shelf_gap for i, y in enumerate(visible_baselines)}

fig, ax = plt.subplots(figsize=(14, 3.2 * n_visible))
fig.patch.set_facecolor("#F8F4EE")
ax.set_facecolor("#F8F4EE")
ax.set_xlim(-2, shelf_width + 2)
ax.set_ylim(-1, n_visible * shelf_gap + 2)
ax.set_aspect("equal")
ax.axis("off")
fig.suptitle("Store Shelf Layout", fontsize=15, fontweight="bold", color="#2E5339", y=1.01)

# Build a set of highlighted product ids from the SKU search
highlighted_skus = set()
if sku_search:
    for item in filtered_data:
        highlighted_skus.add(item["products"].get("sku"))

for raw_y, display_y in baseline_map.items():
    shelf_num  = y_to_shelf[raw_y]
    color      = SHELF_COLORS[(shelf_num - 1) % len(SHELF_COLORS)]

    # Back panel
    ax.add_patch(patches.Rectangle(
        (0, display_y), shelf_width, shelf_gap - 1,
        facecolor="#EDE3D3", edgecolor="none", zorder=1, alpha=0.6
    ))
    # Shelf board
    ax.add_patch(patches.Rectangle(
        (0, display_y - 1.2), shelf_width, 1.2,
        facecolor="#8B6340", edgecolor="#5C3D1E", linewidth=0.8, zorder=3
    ))
    # Side brackets
    for bx in [0, shelf_width]:
        ax.add_patch(patches.Rectangle(
            (bx - 0.8 if bx > 0 else bx, display_y - 1.2),
            0.8, shelf_gap, facecolor="#6B4C2A", edgecolor="none", zorder=2
        ))
    # Shelf label
    ax.text(-1.2, display_y + shelf_gap / 2, f"Shelf {shelf_num}",
            fontsize=8, fontweight="bold", color="#5C3D1E",
            va="center", ha="right", rotation=90)

    # All products on this shelf (draw dim ones first, bright ones on top)
    shelf_items = [item for item in all_data if item["y_pos"] == raw_y]
    for item in shelf_items:
        p   = item["products"]
        x, w, h = item["x_pos"], p["width_in"], p["height_in"]
        sku = p.get("sku")

        is_visible   = item in filtered_data
        face_color   = color if is_visible else "#CCCCCC"
        face_alpha   = 0.88 if is_visible else 0.3
        label_color  = "white" if is_visible else "#999999"

        ax.add_patch(FancyBboxPatch(
            (x + 0.15, display_y + 0.15), w - 0.3, h - 0.3,
            boxstyle="round,pad=0.1",
            facecolor=face_color, edgecolor="white",
            linewidth=1.2, alpha=face_alpha, zorder=4
        ))

        if is_visible:
            # Highlight ring for search matches
            if sku_search and sku in highlighted_skus:
                ax.add_patch(FancyBboxPatch(
                    (x + 0.05, display_y + 0.05), w - 0.1, h - 0.1,
                    boxstyle="round,pad=0.1",
                    facecolor="none", edgecolor="#FFD700",
                    linewidth=2.5, zorder=5
                ))
            # Top highlight sheen
            ax.add_patch(patches.Rectangle(
                (x + 0.3, display_y + h - 1.8), w - 0.6, 1.4,
                facecolor="white", alpha=0.18, zorder=5
            ))

        # Label
        words = p["name"].split()
        lines, line = [], ""
        for word in words:
            if len(line) + len(word) > 10 and line:
                lines.append(line.strip())
                line = word + " "
            else:
                line += word + " "
        if line:
            lines.append(line.strip())

        ax.text(x + w / 2, display_y + h / 2, "\n".join(lines),
                ha="center", va="center", fontsize=6.2,
                color=label_color, fontweight="bold", zorder=6,
                path_effects=[pe.withStroke(linewidth=1.5, foreground="black")])

plt.tight_layout()
st.pyplot(fig, use_container_width=True)

# ── Sortable table ────────────────────────────────────────────────────────────
st.subheader("Product Placement")

rows = []
for item in filtered_data:
    p = item["products"]
    rows.append({
        "Shelf":   y_to_shelf[item["y_pos"]],
        "Product": p["name"],
        "SKU":     p.get("sku", ""),
        "x (in)":  item["x_pos"],
        "W (in)":  p["width_in"],
        "H (in)":  p["height_in"],
    })

rows.sort(key=lambda r: r[sort_col], reverse=not sort_asc)
st.dataframe(rows, use_container_width=True, hide_index=True)
