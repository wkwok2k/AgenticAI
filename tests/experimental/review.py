from pathlib import Path
from typing import Dict, List, Optional, Tuple
import streamlit as st
import yaml

#---- Contig----
DEFAULT_CONFIG_DIR = Path("src/agenticai/configs/sql/analysis")

#---- Helpers ----
@st.cache_data(show_spinner=False)
def discover_yaml_files(root: Path) -> Dict[str, Path]:
    """Returns a map: report_name -› file_path. Report name is derived from the YAML filename (stem), e.g. analysis 20520~Loans.yml -> analysis 2052a~Loans"""
    files: Dict[str, Path] = {}
    if not root.exists():
        return files

    for p in root.rglob("*.ym|"):
        files[p.stem] = p
    for p in root.rglob("*.yaml"):
        files[p.stem] = p

    return dict(sorted(files.items(), key=lambda kv: kv[0].lower()))

@st.cache_data(show_spinner=False)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def stem_to_report_name(stern: str) -> str:
    """If your convention is analysis_<report>.yml strip leading ‘analysis.’ so dropdown shows ‘2052a -Loans’. Otherwise it will just show the stem."""
    prefix = "analysis_"
    return stem[len(prefix) :] if stem.startswith(prefix) else stem

def report_name_to_stem(report_name: str, available_stems: List[str]) -> Optional[str]:
    """
    Given '2052a~Loans', find matching stem:
    - exact stem match
    - or 'analysis_" + report_name match
    - or best-effort contains match
    """

    if report_name in available_stems:
        return report_name

    candidate = f"analysis_{report_name}"
    if candidate in available_stems:
        return candidate

    # best-effort: find the first stem that ends with the report name (common with prefixes)
    for s in available_stems:
        if s.endswith(report_name):
            return s

    return None

# UI
st.set_page_config(page_title="Report YAML Viewer", layout= "wide")
st.markdown(
  """
  ‹style>
    block-container { padding-top: 1 rem; padding-bottom: 1rem;}
  </style>
  """, unsafe_allow_html= True
)

st.title(" Report Config Viewer (VAML)")
with st.sidebar:
    st.header("Config location")
    config_dir_str = st.text_input(
        "Directory containing report YAML files",
        value=str(DEFAULT_CONFIG_DIR),
        key="config_dir_input",
        help="Example: src/agenticaj/configs/sql/analysis",
    )
    config_dir = Path(config_dir_str).expanduser()

    # st.caption("Tip: filenames like "analysis_2052a~Loans.yml" will show as "2052a~Loans" in the dropdown.")
    st.header("Approval for break_summary update")
    approve = st.checkbox("Approve", key="approve_checkbox")
    reject = st.checkbox ("Reject", key="reject_checkbox")

    if approve:
      st.sidebar.success("Queued for batch update.")

    if reject:
        # st.sidebar.error("Please provide context."]
        reason = st.sidebar.text_area("Please provide context", key="rejection_reason", placeholder="")
        if st.sidebar.button ("Submit"):
            if reason.strip():
                st.sidebar.success ("Rejection reason submitted.")
            else:
                st.sidebar.error("Please provide a reason before submitting.")

yaml_map = discover_yaml_files(config_dir)
if not yaml_map:
    st.error(
        f"No .yml/.yaml files found under: {config_dir.resolve()}\n\n"
        "Check the directory path or make sure the repo is mounted correctly."
    )
    st.stop()

# Build dropdown labels (friendly report names) while keeping mapping back to stem/path
stem_list = list(yaml_map.keys())
report_labels: List[Tuple[str, str]] = [(stem_to_report_name(stem), stem) for stem in stem_list]

# Ensure uniqueness of labels (in case two stems map to same label)
label_counts = {}
display_items = []
for label, stem in report_labels:
    label_counts[label] = label_counts.get(label, 0) + 1
for label, stem in report_labels:
    if label_counts[label] > 1:
        display_items.append(f"{label} ({stem})")
    else:
        display_items.append(label)

# Session state for "Load" behavior (so selection doesn't immediately overwrite content unless you click)
if "loaded_stem" not in st.session_state:
    st.session_state.loaded_stem = None
if "loaded_content" not in st.session_state:
    st.session_state.loaded_content = ""

#--- Compact: dropdown + Load + Refresh in one row ---
col_sel, col_load, col_ref = st.columns([6, 1, 1], gap="small")

with col_sel:
    selected_display = st.selectbox(
        "Select report",
        options=display_items,
        index=0,
        key="report_selectbox_unique_key",
        label_visibility="collapsed", # removes extra vertical space
    )

# Resolve selected stem (same logic you had)
selected_stern: Optional[str]
if selected_display.endswith(")") and " (" in selected_display:
    selected_stem = selected_display.rsplit(" (", 1)[1].rstrip(")")
else:
    reverse = {stem_to_report_name(s): s for s in stem_list}
    selected_stem = reverse.get(selected_display)

with col_load:
    load_clicked = st.button(
        "Load",
        key="load_button_unique_key",
        use_container_width= True,
    )

with col_ref:
    refresh_clicked = st.button(
        "I",
        key="refresh_button_unique_key",
        use_container_width=True,
        help="Refresh file list",
    )

if refresh_clicked:
    st.cache_data.clear()
    st.rerun()

if load_clicked:
    if not selected_stem:
        st.error("Could not resolve selection to a YAML file stem.")
    else:
        path = yaml_map[selected_stem]
        try:
            st.session_state.loaded_stem = selected_stem
            st.session_state.loaded_content = read_text(path)
            # st.toast(f"Loaded: [path.name]", icon="V")
        except Exception as e:
            st.error(f"Failed to read file: {path}\n\n{e}")

loaded_stem = st.session_state.loaded_stem
loaded_content = st.session_state.loaded_content

if not loaded_stem:
    st.info("Pick a report and click **Load selection** to display its YAML content.")
    st.stop()

loaded_path = yaml_map.get(loaded_stem)

st.subheader ("Selected file")
if loaded_path:
    st.write(f"**Report:** `{stem_to_report_name(loaded_stem)}`")
else:
    st.warning("Previously loaded file is no longer present in the directory. Refresh and load again.")

tabs = st.tabs(["Raw YAML", "Parsed (if available)"])

with tabs[0]:
    st.code(loaded_content, language="yaml")

with tabs[1]:
    if yaml is None:
        st.warning("PyYAML not installed in this environment, so parsed view is unavailable.")
    else:
        try:
          parsed = yaml.safe_load(loaded_content) # type ignore
          st.json (parsed)
        except Exception as e:
          st.error(f"YAML parse error\n\n{e}")
          st.code(loaded_content, language="yaml")