from pathlib import Path
from typing import Dict, List, Optional, Tuple
import streamlit as st
import yaml

#---- Contig----
DEFAULT_CONFIG_DIR = Path("src/agenticai/configs/sql/analysis")
EXPOSURE_FILE_PATH = Path(__file__).with_name("exposure.yml")
SPARK_BOOTSTRAP = (
    "from pyspark.sql import SparkSession\n"
    "spark = SparkSession.builder\n"
    '   .appName("Update Break Summary with Exposure Amt")\n'
    "   .getOrCreate()"
)
MERGE_STATEMENT = (
    "spark.sql(\"\"\"\n"
    "MERGE INTO om_onerec_break_summary AS target\n"
    "USING (\n"
    "    SELECT hierarchy_path, recon_run_date, hop_id, exposure_amt\n"
    "    FROM approved_exposure_updates\n"
    "    WHERE post_processing_summary = 'Y'\n"
    ") AS source\n"
    "ON target.hierarchy_path = source.hierarchy_path\n"
    "AND target.recon_run_date = source.recon_run_date\n"
    "AND target.hop_id = source.hop_id\n"
    "AND target.post_processing_summary = 'Y'\n"
    "WHEN MATCHED THEN\n"
    "    UPDATE SET target.exposure_amt = source.exposure_amt\n"
    "\"\"\")"
)

#---- Helpers ----
@st.cache_data(show_spinner=False)
def discover_yaml_files(root: Path) -> Dict[str, Path]:
    """Returns a map: report_name -› file_path. Report name is derived from the YAML filename (stem), e.g. analysis 20520~Loans.yml -> analysis 2052a~Loans"""
    files: Dict[str, Path] = {}
    if not root.exists():
        return files

    for p in root.rglob("*.yml"):
        files[p.stem] = p
    for p in root.rglob("*.yaml"):
        files[p.stem] = p

    return dict(sorted(files.items(), key=lambda kv: kv[0].lower()))

@st.cache_data(show_spinner=False)
def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")

def stem_to_report_name(stem: str) -> str:
    """If your convention is analysis_<report>.yml strip leading ‘analysis.’ so dropdown shows ‘2052a -Loans’. Otherwise it will just show the stem."""
    prefix = "analysis_"
    return stem[len(prefix) :] if stem.startswith(prefix) else stem

def append_merge_to_exposure_queue() -> Tuple[bool, bool]:
    """
    Appends merge statement into `queued` in exposure.yml.
    Returns (was_appended, file_created).
    """
    file_created = not EXPOSURE_FILE_PATH.exists()
    payload: Dict[str, object] = {}

    if EXPOSURE_FILE_PATH.exists():
        try:
            parsed = yaml.safe_load(EXPOSURE_FILE_PATH.read_text(encoding="utf-8"))
            if isinstance(parsed, dict):
                payload = parsed
        except Exception:
            payload = {}

    queued = payload.get("queued")
    if not isinstance(queued, list):
        queued_list: List[str] = []
    else:
        queued_list = [str(item) for item in queued]

    if file_created and SPARK_BOOTSTRAP not in queued_list:
        queued_list.append(SPARK_BOOTSTRAP)

    if MERGE_STATEMENT in queued_list:
        payload["queued"] = queued_list
        EXPOSURE_FILE_PATH.write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
            encoding="utf-8",
        )
        return False, file_created

    queued_list.append(MERGE_STATEMENT)
    payload["queued"] = queued_list
    EXPOSURE_FILE_PATH.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )
    return True, file_created

def reset_approval_controls() -> None:
    st.session_state["approve_checkbox"] = False
    st.session_state["reject_checkbox"] = False
    st.session_state["_approve_previous_value"] = False
    st.session_state["rejection_reason"] = ""

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
    previous_approve = st.session_state.get("_approve_previous_value", False)
    approve = st.checkbox("Approve", key="approve_checkbox")
    reject = st.checkbox ("Reject", key="reject_checkbox")

    if approve and not previous_approve:
        appended, created = append_merge_to_exposure_queue()
        if appended and created:
            st.sidebar.success("Queued for batch update. Created exposure.yml and appended merge statement once.")
        elif appended:
            st.sidebar.success("Queued for batch update. Appended merge statement once.")
        else:
            st.sidebar.info("Merge statement already exists in exposure.yml queued list. Skipped duplicate append.")

    st.session_state["_approve_previous_value"] = approve

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
        on_click=reset_approval_controls,
        use_container_width= True,
    )

with col_ref:
    refresh_clicked = st.button(
        "I",
        key="refresh_button_unique_key",
        on_click=reset_approval_controls,
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
