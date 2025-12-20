def generate_from_config
if not input_prompt or not str(input_prompt).strip():
    raise ValueError(
        f"[VertexGenAI] input_prompt empty after rendering. agent_config_name={agent_config_name}, "
        f"template_vars={template_vars}"
    )
