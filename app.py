import os
import base64
import requests
import streamlit as st
from supabase import create_client
import plotly.graph_objects as go


@st.cache_data(ttl=3600)
def fetch_image_b64(url: str) -> str:
    """Fetch an image and return it as a base64 data URI.
    Caching avoids re-fetching on every Streamlit rerun.
    Using base64 sidesteps browser CORS restrictions on external image URLs."""
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        mime = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        b64  = base64.b64encode(resp.content).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""

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

# ── Session state ─────────────────────────────────────────────────────────────
if "selected_skus" not in st.session_state:
    st.session_state.selected_skus = set()

# Clear flag must be processed BEFORE the text_input widget is created,
# otherwise Streamlit raises an error for setting a bound widget's key.
if st.session_state.get("_clear_search"):
    st.session_state._clear_search = False
    st.session_state.sku_search = ""

# ── Raw data ──────────────────────────────────────────────────────────────────
response = supabase.table("shelf_layout").select("*, products(*)").execute()
all_data = response.data

if not all_data:
    st.warning("No shelf layout data found.")
    st.stop()

all_baselines = sorted(set(item["y_pos"] for item in all_data))
y_to_shelf    = {y: i + 1 for i, y in enumerate(all_baselines)}
shelf_width   = 48
shelf_gap     = 18
SHELF_COLORS  = ["#E07B39", "#4A7C59", "#5B8DB8", "#C0392B", "#8E6BBF"]

def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def wrap_label(name, max_chars=10):
    words, lines, line = name.split(), [], ""
    for w in words:
        if len(line) + len(w) > max_chars and line:
            lines.append(line.strip())
            line = w + " "
        else:
            line += w + " "
    if line:
        lines.append(line.strip())
    return "<br>".join(lines)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters & Sorting")

    shelf_options       = [f"Shelf {y_to_shelf[y]}" for y in all_baselines]
    selected_shelves    = st.multiselect("Shelves", shelf_options, default=shelf_options)
    selected_shelf_nums = {int(s.split()[1]) for s in selected_shelves}

    # Search box with its own clear button
    sku_search = st.text_input("Search by product name or SKU", key="sku_search")
    if sku_search:
        if st.button("✕ Clear search", use_container_width=True):
            st.session_state._clear_search = True
            st.rerun()

    st.divider()
    sort_col = st.selectbox("Sort table by",
                            ["Shelf", "Product", "SKU", "x (in)", "W (in)", "H (in)"])
    sort_asc = st.radio("Order", ["Ascending", "Descending"]) == "Ascending"

    st.divider()
    if st.button("Clear selection", use_container_width=True):
        st.session_state.selected_skus = set()
        st.rerun()

    if st.session_state.selected_skus:
        st.caption(f"**{len(st.session_state.selected_skus)}** product(s) selected")
    else:
        st.caption("Click a product to select it")
    st.caption("Drag to box-select multiple products")

# ── Filter ────────────────────────────────────────────────────────────────────
def matches(item):
    if y_to_shelf[item["y_pos"]] not in selected_shelf_nums:
        return False
    if sku_search:
        q = sku_search.lower()
        p = item["products"]
        if q not in p["name"].lower() and q not in (p.get("sku") or "").lower():
            return False
    return True

filtered_data = [item for item in all_data if matches(item)]
any_selected  = bool(st.session_state.selected_skus)

# ── Metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
total_w = sum(item["products"]["width_in"] for item in filtered_data)
c1.metric("SKUs Shown",    f"{len(filtered_data)} / {len(all_data)}")
c2.metric("Shelves Shown", f"{len({item['y_pos'] for item in filtered_data})} / {len(all_baselines)}")
c3.metric("Linear Feet",   f"{total_w/12:.1f} ft / {shelf_width/12:.0f} ft")

st.divider()

# ── Planogram ─────────────────────────────────────────────────────────────────
visible_baselines = [y for y in all_baselines
                     if y_to_shelf[y] in selected_shelf_nums
                     and any(item["y_pos"] == y for item in filtered_data)]
n_visible    = max(len(visible_baselines), 1)
baseline_map = {y: i * shelf_gap for i, y in enumerate(visible_baselines)}

fig = go.Figure()
fig.update_layout(
    clickmode="event+select",
    plot_bgcolor="#F8F4EE",
    paper_bgcolor="#F8F4EE",
    showlegend=False,
    margin=dict(l=60, r=20, t=40, b=20),
    xaxis=dict(range=[-3, shelf_width + 2], showgrid=False, zeroline=False,
               showticklabels=True, title="Width (inches)", tickfont=dict(size=10)),
    yaxis=dict(range=[-2, n_visible * shelf_gap + 2], showgrid=False, zeroline=False,
               showticklabels=False, scaleanchor="x", scaleratio=1),
    height=max(280, 260 * n_visible),
    title=dict(text="Store Shelf Layout", font=dict(size=15, color="#2E5339"), x=0.5),
    dragmode="select",
)

# trace index → sku for interactive center-point traces only
trace_sku_map = []

for raw_y, display_y in baseline_map.items():
    shelf_num = y_to_shelf[raw_y]
    color     = SHELF_COLORS[(shelf_num - 1) % len(SHELF_COLORS)]
    r, g, b   = hex_to_rgb(color)

    # Shelf structure — all pure shapes, no hover, no interaction
    fig.add_shape(type="rect", x0=0, y0=display_y, x1=shelf_width, y1=display_y + shelf_gap - 1,
                  fillcolor="#EDE3D3", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=0, y0=display_y - 1.2, x1=shelf_width, y1=display_y,
                  fillcolor="#8B6340", line=dict(color="#5C3D1E", width=1), layer="below")
    fig.add_shape(type="rect", x0=-0.8, y0=display_y - 1.2, x1=0, y1=display_y + shelf_gap - 1,
                  fillcolor="#6B4C2A", line=dict(width=0), layer="below")
    fig.add_shape(type="rect", x0=shelf_width, y0=display_y - 1.2,
                  x1=shelf_width + 0.8, y1=display_y + shelf_gap - 1,
                  fillcolor="#6B4C2A", line=dict(width=0), layer="below")
    fig.add_annotation(x=-1.5, y=display_y + shelf_gap / 2,
                       text=f"<b>Shelf {shelf_num}</b>", showarrow=False,
                       font=dict(size=9, color="#5C3D1E"), textangle=-90)

    shelf_items = [item for item in all_data if item["y_pos"] == raw_y]
    for item in shelf_items:
        p   = item["products"]
        x, w, h = item["x_pos"], p["width_in"], p["height_in"]
        sku = p.get("sku", "")

        is_filtered = item in filtered_data
        is_selected = sku in st.session_state.selected_skus

        if not is_filtered:
            fc, lc, lw, opacity = "rgba(200,200,200,0.25)", "rgba(180,180,180,0.3)", 1, 0.4
        elif any_selected and not is_selected:
            fc, lc, lw, opacity = f"rgba({r},{g},{b},0.22)", "rgba(255,255,255,0.35)", 1, 0.5
        elif is_selected:
            fc, lc, lw, opacity = f"rgba({r},{g},{b},0.95)", "rgba(255,215,0,1)", 3, 1.0
        else:
            fc, lc, lw, opacity = f"rgba({r},{g},{b},0.85)", "rgba(255,255,255,0.9)", 1.5, 1.0

        image_url = p.get("image_url") or ""
        # Fetch server-side and encode as base64 so Plotly never makes a
        # cross-origin request from the browser (avoids CORS failures).
        image_src = fetch_image_b64(image_url) if image_url and is_filtered else ""
        has_image = bool(image_src)

        # ── Visual rectangle — border always drawn; fill only when no image ──
        fig.add_shape(
            type="rect",
            x0=x + 0.15, y0=display_y + 0.15,
            x1=x + w - 0.15, y1=display_y + h - 0.15,
            fillcolor=fc if not has_image else "rgba(0,0,0,0)",
            line=dict(color=lc, width=lw),
            opacity=opacity,
            layer="above",
        )

        # ── Product image overlay (when image_url is set) ────────────────────
        if has_image:
            fig.add_layout_image(dict(
                source=image_src,
                xref="x", yref="y",
                x=x + 0.25,
                y=display_y + h - 0.25,   # plotly image anchor is top-left
                sizex=w - 0.5,
                sizey=h - 0.5,
                sizing="stretch",
                opacity=1.0 if not (any_selected and not is_selected) else 0.25,
                layer="above",
            ))

        # ── Invisible center point — the ONLY thing with hover and selection ─
        # A single point at the product center means:
        #   • exactly one tooltip fires per product (no duplicate)
        #   • box-drag just needs to cross the center to select the product
        if is_filtered:
            fig.add_trace(go.Scatter(
                x=[x + w / 2],
                y=[display_y + h / 2],
                mode="markers",
                marker=dict(size=2, opacity=0.01, color="rgba(0,0,0,0)"),
                name=p["name"],
                hovertemplate=(
                    f"<b>{p['name']}</b><br>"
                    f"SKU: {sku}<br>"
                    f"Shelf {shelf_num}<br>"
                    f"x={x}\" &nbsp;|&nbsp; {w}\"×{h}\""
                    "<extra></extra>"
                ),
                showlegend=False,
                selected=dict(marker=dict(opacity=0.01)),
                unselected=dict(marker=dict(opacity=0.01)),
            ))
            trace_sku_map.append(sku)

        # ── Product label (hidden when image fills the box) ───────────────────
        if is_filtered and not has_image:
            label_color = ("rgba(255,255,255,1.0)"
                           if not (any_selected and not is_selected)
                           else "rgba(255,255,255,0.3)")
            fig.add_annotation(
                x=x + w / 2, y=display_y + h / 2,
                text=f"<b>{wrap_label(p['name'])}</b>",
                showarrow=False,
                font=dict(size=6.5, color=label_color),
                bgcolor="rgba(0,0,0,0)",
                align="center",
            )

# ── Render + handle selection events ─────────────────────────────────────────
event = st.plotly_chart(
    fig,
    on_select="rerun",
    selection_mode=["points", "box", "lasso"],
    use_container_width=True,
)

if event and event.selection and event.selection.points is not None:
    clicked_skus = set()
    for pt in event.selection.points:
        idx = pt.get("curve_number")
        if idx is not None and idx < len(trace_sku_map):
            clicked_skus.add(trace_sku_map[idx])
    if clicked_skus != st.session_state.selected_skus:
        st.session_state.selected_skus = clicked_skus
        st.rerun()

# ── Table ─────────────────────────────────────────────────────────────────────
st.subheader("Product Placement")

table_data = filtered_data
if st.session_state.selected_skus:
    table_data = [item for item in filtered_data
                  if item["products"].get("sku") in st.session_state.selected_skus]

rows = []
for item in table_data:
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
