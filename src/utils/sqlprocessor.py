import json, os
import pandas as pd
from collections import defaultdict
from utils.logconfig import step_log
from utils.yaml_loader import render_sql_from_yaml

async def generate_sql(yaml_file, params):
    """ Generate SQL from YAML file and parameters. """
    try:
        sql = render_sql_from_yaml(yaml_file, **params)
        if sql is None:
            step_log("SQL generation returned None")
        return sql
    except Exception as e:
        step_log(f"Error generating SQL: {e}")
        return None

