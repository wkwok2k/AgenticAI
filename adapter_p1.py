    def generate_from_config(
        self,
        agent_config_name: str,
        template_vars: Optional[Dict[str, Any]] = None,
        json_mode: bool = False,
        tools: Optional[list] = None,
    ) -> Any:
        cfg = self._load_agent_config(agent_config_name)

        system_prompt_tpl = cfg.get("system_prompt", "") or ""
        task_prompt_tpl = cfg.get("task_prompt", "") or ""
        model_name = cfg.get("model_name", "gemini-2.0-flash-001")
        temperature = float(cfg.get("temperature", 0.0))

        # Render prompts (StrictUndefined will throw if user_question missing)
        system_prompt = self._render(system_prompt_tpl, template_vars or {}) if system_prompt_tpl.strip() else ""
        input_prompt = self._render(task_prompt_tpl, template_vars or {}) if task_prompt_tpl.strip() else ""

        # 🔴 HARD GUARDS (this prevents the Vertex "contents must not be empty" error)
        if not input_prompt or not input_prompt.strip():
            raise ValueError(
                f"[VertexGenAI] Rendered task_prompt is empty. "
                f"agent_config_name={agent_config_name}, template_vars={template_vars}"
            )

        gen_config_kwargs = dict(temperature=temperature)
        if json_mode:
            gen_config_kwargs["response_mime_type"] = "application/json"
            gen_config_kwargs["seed"] = 42

        model = GenerativeModel(
            model_name=model_name,
            system_instruction=[system_prompt] if system_prompt.strip() else None,
            generation_config=GenerationConfig(**gen_config_kwargs),
            tools=tools,
        )

        resp = model.generate_content(input_prompt)

        # If json_mode, parse JSON safely
        if json_mode:
            text = getattr(resp, "text", None) or ""
            text = text.strip()
            if not text:
                raise ValueError(f"[VertexGenAI] JSON mode response empty for {agent_config_name}")

            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"[VertexGenAI] JSON parse failed: {e}. Raw: {text[:500]}")

        # Non-JSON: return plain text
        return getattr(resp, "text", str(resp))
