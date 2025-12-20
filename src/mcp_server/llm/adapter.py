import os, json, requests, traceback, asyncio, datetime, ast, time, yaml, vertexai
from typing import Any, Dict, List, Optional
from jinja2 import Environment, StrictUndefined
from pathlib import Path
from vertexai_generative_models import (GenerativeModel, GenerationConfig)
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv
from utils.logconfig import step_log

load_dotenv()

# Set the certificate bundle path
os.environ["REQUESTS_CA_BUNDLE"] = "./.certs/sertprod-pem"
LOG_FILE = "logs/query_logs.json"

def get_access_token():
    url = "https://aaabbb.com/token/v2/d8ba..."
    headers = {
        "accept": "*/*",
        "Content-Type": "application/json",
    }

    data = {
        "clientSecret": "abcdefghijklmn", # one time process
        "clientScopes": ["abcdef12-6e52-..."] # read/ write scope
    }

    response = requests.post(url, headers=headers, json=data)
    # Check for successful response
    if response.status_code == 200:
        return response.text
    else:
        return response.status_code

class VertexGenAI:
    def __init__(self, default_model: Optional[str] = None):
        self.default_model = (default_model or
                               os.getenv("VERTEX_MODEL_NAME",
                                         "gemini-2.0-flash-001"))
        self.default_temperature = float(os.getenv("VERTEX _TEMPERATURE", "0.0"))
        self.default_seed = int(os.getenv("VERTEX_SEED", "42"))
        self.metadata = [("gw-user", os.getenv("USERNAME"))]

        credentials = Credentials(get_access_token())
        vertexai.init(
            project="pr123434",
            api_transport="rest",
            api_endpoint="https://abcde.com.....",
            credentials=credentials,
        )

    def _load_agent_config(self, agent_config_name: str) -> Dict[str, Any]:
        cfg_dir = Path(__file__).resolve().parents[1] / "agents" / "configs"
        cfg_path = cfg_dir / f"{agent_config_name}.yml"
        if not cfg_path.exists():
            raise FileNotFoundError(f"Agent config not found: (cfg_path)")

        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
            return cfg

    def _render(self, template: str, template_vars: dict) -> str:
        env = Environment(undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
        safe_vars = dict(template_vars or {})
        safe_vars.setdefault("recent_turns", "")
        safe_vars.setdefault("last_answer", "")
        return env.from_string(template).render(**safe_vars)

    def generate_content(
        self,
        input_prompt,
        system_prompt: Optional[str] = None,
        gemini_model: Optional[str] = None,
        temperature: Optional[float] = None,
        seed: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate plain/text content using Gemini."""
        step_log(message: "AgenticAI - generate_content: Start", 0)
        start_time = time.time()

        model = self._build_model(
            system_prompt=system_prompt,
            gemini_model = gemini_model,
            response_mime_type = "text/plain",
            temperature = temperature,
            seed = seed,
        )

        try:
            resp = model.generate_content(input_prompt) # metadata=self.metadata,
        except Exception as e:
            elapsed_time = time.time() - start_time
            step_log( message: f"AgenticAI - generate_content: Error {e}", elapsed_time)
            raise

        elapsed_time = time.time() - start_time
        step_log( message: "AgenticAI - generate_content: Completed", elapsed_time)

        self._log_entry(
            {
                "kind": "text",
                "system_prompt": system_prompt,
                "model_name": gemini_model or self.default_model,
                "temperature": temperature if temperature is not None else self.default_temperature,
                "metadata": metadata or {},
                "raw_response": str(resp),
            }
        )

        try:
            text = "".join([p.text for p in resp.candidates[0].content.parts])
        except Exception:
            text = str(resp)

        return self._clean_unicode(text)

    def generate_content_json(
            self,
            input_prompt,
            system_prompt: Optional[str] = None,
            gemini_model: Optional[str] = None,
            temperature: Optional[float] = None,
            seed: Optional[int] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate JSON using response_mime_type = "application/json"
            Returns a python dict. If parsing fails, returns {"error", "..."}"""
        start_time = time.time()
        step_log(message: "AgenticAI - generate_content_jsons Start", 0)

        model = self._build_model(
            system_prompt = system_prompt,
            gemini_model = gemini_model,
            esponse_mime_type = "application/json",
            temperature = temperature,
            seed = seed,
        )

        try:
            resp = model.generate_content(input_prompt)  # metadata=self.metadata
        except Exception as e:
            elapsed_time = time.time() - start_time
            step_log(message: f"AgenticAI - generate_content_json: Error {e}, traceback: {traceback.format_exc()}", elapsed_time)
            return {"error": str(e)}

        elapsed_time = time.time() - start_time
        step_log(message: f"AgenticAI - generate_content_json: Completed", elapsed_time)

        self._log_entry(
            {
                "kind": "text",
                "input_prompt": input_prompt,
                "system_prompt": system_prompt,
                "model_name": gemini_model or self.default_model,
                "temperature": temperature if temperature is not None else self.default_temperature,
                "metadata": metadata or {},
                "raw_response": str(resp),
            }
        )

        try:
            raw = "".join([p.text for p in resp.candidates[0].content.parts])
            parsed = json.loads(raw)
            return parsed
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON response: {e}")
            return {"Error": "Invalid JSON response"}
        except Exception as e:
            print(f"Error generating content: {e}, traceback: {traceback.format_exc()}")
            return {"Error": str(e)}

    def _load_agent_yaml(
            self,
            agent_config_name: str
    ) -> Dict[str, Any]:
        """ Load an agent config YAML from agents/configs/<name>.yml """
        base_dir = os.path.dirname(os.path.dirname(__file__))  # mcp_server/
        yaml_path = os.path.join(
            base_dir, "agents", "configs", f"{agent_config_name}.yml"
        )

        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Agent config not found: {yaml_path}")

        with open(yaml_path, "r", encoding="utf-8") as f:
            return json.loads(json.dumps(__import__("yaml").safe_load(f)))

    @staticmethod
    def _clean_unicode(text: str) -> str:
        """ Remove non-ASCII characters from text. """
        return text.encode("utf-8", "ignore").decode("utf-8")

    @staticmethod
    def _log_entry(entry: Dict[str, Any]) -> None:
        """ Append a JSON entry to the LOG_FILE. (simple list). """
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r', encoding="utf-8") as f:
                    try:
                        logs = json.load(f)
                    except json.JSONDecodeError:
                        logs = []
            else:
                logs = []

            # if logs is not a list (because you are using dict structure elsewhere)
            # skip this logging to avoid clobbering.
            if not isinstance(logs, list):
                return

            logs.append(entry)
            with open(LOG_FILE, 'w', encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

        except Exception:
            pass

    def _build_mode(
            self,
            system_prompt: Optional[str] = None,
            gemini_model: Optional[str] = None,
            response_mime_type: Optional[str] = None,
            temperature: Optional[float] = None,
            seed: Optional[int] = None,
    ) -> GenerativeModel:
        """ Build and return a GenerativeModel instance """
        model_name = gemini_model or self.default_model
        temp = self.default_temperature if temperature is None else temperature
        seed_val = self.default_seed if seed is None else seed

        gen_cfg = GenerationConfig(
            respones_mime_type = response_mime_type,
            temperature = temp,
            seed = seed_val
        )

        kwargs: Dict[str, Any] = { "generation_config": gen_cfg }
        if system_prompt:
            kwargs["system_instruction"] = [system_prompt]

        model = GenerativeModel(model_name, **kwargs)
        return model

    def generate_from_config(
            self,
            agent_config_name: str,
            template_vars: Dict[str, Any],
            json_mode: bool = False,
            tools: Optional[List] = None,
    ) -> Any:
        cfg_yaml = self._load_agent_yaml(agent_config_name)

        system_prompt_template = cfg_yaml.get("system_prompt", "")
        task_prompt_template = cfg_yaml.get("task_prompt", "")
        model_name = cfg_yaml.get("model_name") or self.default_model
        temperature = float(cfg_yaml.get("temperature", self.default_temperature))

        # Render prompts (StrictUndefined will throw if user_question is missing)
        system_prompt = self._render(system_prompt_template, template_vars or {}) if system_prompt_template.strip() else ""
        input_prompt = self._render(task_prompt_template, template_vars or {}) if task_prompt_template.strip() or ""

        if not input_prompt or not str(input_prompt).strip():
            raise ValueError(
                f"[VertexGenAI] input_prompt empty after rendering. agent_config_name={agent_config_name}."
                f"template_vars={template_vars}"
            )

        gen_config_kwargs = dict(temperature=temperature)
        if json_mode:
            gen_config_kwargs["response_mime_type"] = "application/json"
            gen_config_kwargs["seed"] = 42

        model = GenerativeModel(
            model_name = model_name,
            system_instruction = [system_prompt] if system_prompt.strip() else None,
            generation_config = GenerationConfig(**gen_config_kwargs),
            tools = tools,
        )

        resp = model.generate_content(input_prompt)

        if json_mode:
            text = getattr(resp, "text", None) or ""
            text = text.strip()
            if not text:
                raise ValueError(f"[VertexGenAI] JSON mode response empty for {agent_config_name}")

            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"[VertexGenAI] JSON parse failed: {e}. Raw: {text[:500]}")

        return getattr(resp, "text", str(resp))

# -------------------------------------------------------------------
completed_tasks = 0
total_tasks = 0
progress_lock = asyncio.Lock()

async def generalize_result(llm_response,
                            user_query,
                            gemini_model,
                            system_prompt):
    global completed_tasks

    input_prompt = f"data_set {llm_response} and user_query {user_query}"
    try:
        loop = asyncio.get_event_loop()
        print("Reading and Processing")
        response = await loop.run_in_executor(
            None,
            get_vertex_object().generate_content_json,
            input_prompt,
            system_prompt,
            gemini_model
        )

        output = []
        if hasattr(response, 'candidates') and response.candidates:
            response_text = response.candidates[0].content.parts[0].text
            parsed_response = ast.literal_eval(response_text)
            return parsed_response
        else:
            return "NULL"

    except Exception as e:
        print(f"Error processing chunk: {e}, traceback: {traceback.format_exc()}")
        return []
    finally:
        async with progress_lock:
            global completed_tasks
            completed_tasks += 1
            end_time = time.time()

# -----------------------------------------------------------
# Singleton-style accessor with 28-minute refresh
# -----------------------------------------------------------
_vertex_object: Optional[VertexGenAI] = None
_vertex_object_init_time: Optional[datetime.datetime] = None

def get_vertex_object() -> VertexGenAI:
    """ Return a shared VertexGenAI instance, refreshing it every 28 minutes. """
    global _vertex_object, _vertex_object_init_time

    now = datetime.datetime.now()
    if (
        _vertex_object is None
        or _vertex_object_init_time is None
        or (now - _vertex_object_init_time).total_seconds() > 28 * 60
    ):
        _vertex_object = VertexGenAI()
        _vertex_object_init_time = now
        print("Refreshing VertexGenAI object/token")

        return _vertex_object

# -----------------------------------------------------------
# Helper: read past user queries from the log file
# -----------------------------------------------------------
def get_user_queries(
        user_id: str,
        session_id: str,
        log_file: str = LOG_FILE,
) -> List[tuple[str, str]]:
    if not os.path.exists(log_file):
        return []

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

    user_sessions = logs.get(user_id, {}).get(session_id, {})
    results: List[tuple[str, str]] = []

    for req in user_sessions.values():
        uq = req.get("user_query", "")
        gr = req.get("generalized_response", "")
        if uq or gr:
            results.append((uq, gr))

    return results

