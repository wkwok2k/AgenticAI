from typing import Dict
from jinja2 import Template
from importlib import resources
from enum import Enum
import yaml, re

def load_yaml(name: str) -> Dict:
    """ Load a YAML file and return its contents as a dictionary. """
    path = None

    try:
        path = resources.files("mcp_server.configs") / f"{name}.yml"
        return yaml.safe_load(path.read_text())
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {path}")

def render_prompt(prompt_dict: Dict, **kwargs) -> str:
    """ Render system + user parts using Jinja2 and return a single string. """
    system = prompt_dict.get("system", "")
    user = prompt_dict.get("user", "")
    combined = system + "\n" + user
    tpl = Template(combined)
    return tpl.render(**kwargs)

def render_sql(sql_template: str, **kwargs) -> str:
    """ Render a SQL template using Jinja2 and return the rendered SQL string. """
    tpl = Template(sql_template)
    return tpl.render(**kwargs)

def render_sql_from_yaml(yaml_file: str, **kwargs):
    """ Load the SQL template from the YAML file and render it with the provided parameters. """
    sql_config = load_yaml(yaml_file)
    sql_template = sql_config.get("sql", "")
    return render_sql(sql_template, **kwargs)

class SqlCleanMode(Enum):
    CLEAN = "clean"
    CONDENSE = "condense"

def clean_sql(sql: str, mode: SqlCleanMode = SqlCleanMode.CONDENSE) -> str:
    """ Clean SQL by removing comments and white spaces. """
    # Remove single-line comments
    sql = re.sub(r'--.*?(?=\r?\n|$)', '', sql)
    # Remove multi-line comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    if mode == SqlCleanMode.CONDENSE:
        sql = re.sub(r'\s+', ' ', sql).strip()

    return sql