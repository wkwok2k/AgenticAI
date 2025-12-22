import pandas as pd

def split_markdown_table(md: str):
    """
    Returns (prefix_text, table_markdown, suffix_text).
    If no table is found, returns (md, None, "").
    Assumes a GitHub-flavored markdown table:
      header row with |
      separator row with --- and |
    """
    if not md:
        return "", None, ""

    lines = md.splitlines()
    start = None
    end = None

    # Find header + separator pattern
    for i in range(len(lines) - 1):
        if "|" in lines[i] and "|" in lines[i + 1] and set(lines[i + 1].replace("|", "").strip()) <= set("-: "):
            start = i
            break

    if start is None:
        return md, None, ""

    # Table continues while lines contain '|'
    end = start
    for j in range(start, len(lines)):
        if "|" in lines[j]:
            end = j
        else:
            break

    prefix = "\n".join(lines[:start]).strip()
    table_md = "\n".join(lines[start:end + 1]).strip()
    suffix = "\n".join(lines[end + 1:]).strip()
    return prefix, table_md, suffix


def markdown_table_to_df(table_md: str):
    if not table_md:
        return None

    table_lines = [ln.strip() for ln in table_md.splitlines() if ln.strip()]
    if len(table_lines) < 3:
        return None

    header = [c.strip() for c in table_lines[0].strip("|").split("|")]
    # table_lines[1] is separator
    rows = []
    for ln in table_lines[2:]:
        cols = [c.strip() for c in ln.strip("|").split("|")]
        if len(cols) == len(header):
            rows.append(cols)

    if not rows:
        return None

    return pd.DataFrame(rows, columns=header)

analysis_text = data.get("analysis", "") or ""

prefix, table_md, suffix = split_markdown_table(analysis_text)

# Render non-table text normally
if prefix:
    st.markdown(prefix)

# Render table as dataframe to prevent bleed
df = markdown_table_to_df(table_md) if table_md else None
if df is not None:
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    # If table detection failed, just show the whole analysis as markdown
    if analysis_text and not prefix:
        st.markdown(analysis_text)

# Render any trailing text
if suffix:
    st.markdown(suffix)

