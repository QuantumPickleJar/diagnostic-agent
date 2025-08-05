import json
from pathlib import Path

class SemanticTaskScorer:
    """Estimate task complexity using lightweight heuristics"""

    def __init__(self, memory_dir=None):
        self.memory_dir = Path(memory_dir or Path(__file__).parent / "agent_memory")
        self.memory_dir.mkdir(exist_ok=True)
        self.config_file = self.memory_dir / "semantic_config.json"
        self.log_file = self.memory_dir / "recall_log.jsonl"
        self._load_config()
        self._init_embeddings()

    def _load_config(self):
        data = {"enabled": True, "threshold": 0.7}
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    existing = json.load(f)
                data.update(existing)
            except Exception:
                pass
        self.enabled = bool(data.get("enabled", True))
        self.threshold = float(data.get("threshold", 0.7))
        self._save_config()

    def _save_config(self):
        with open(self.config_file, "w") as f:
            json.dump({"enabled": self.enabled, "threshold": self.threshold}, f, indent=2)

    def _init_embeddings(self):
        try:
            from sentence_transformers import SentenceTransformer, util
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            heavy_examples = [
                "optimize algorithm",
                "comprehensive data analysis",
                "compile project"
            ]
            light_examples = [
                "list files",
                "check status",
                "echo hello"
            ]
            self.heavy_emb = self.model.encode(heavy_examples)
            self.light_emb = self.model.encode(light_examples)
            self.util = util
            self.embed_ok = True
        except Exception:
            self.embed_ok = False

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        self._save_config()

    def set_threshold(self, threshold: float):
        self.threshold = float(threshold)
        self._save_config()

    def score(self, text: str) -> float:
        if not self.enabled or not text:
            return 0.0

        score = 0.0
        text_lower = text.lower()

        # Context length and token count
        length_norm = min(len(text) / 1000, 1.0)
        token_norm = min(len(text.split()) / 200, 1.0)
        score += 0.3 * length_norm
        score += 0.3 * token_norm

        # Keyword analysis
        heavy_keywords = [
            "optimize", "analyze", "summarize", "plan", "research",
            "implement", "generate", "build", "develop"
        ]
        light_keywords = ["list", "show", "echo", "simple", "test", "example", "help"]
        if any(k in text_lower for k in heavy_keywords):
            score += 0.2
        if any(k in text_lower for k in light_keywords):
            score -= 0.2

        # Embedding similarity (optional)
        if self.embed_ok:
            emb = self.model.encode([text])
            heavy_sim = float(self.util.cos_sim(emb, self.heavy_emb).max())
            light_sim = float(self.util.cos_sim(emb, self.light_emb).max())
            score += 0.2 * ((heavy_sim - light_sim + 1) / 2)

        return max(0.0, min(1.0, score))

    def log_result(self, task: str, score: float, routed_to: str):
        entry = {
            "task": task,
            "score": round(float(score), 4),
            "routed_to": routed_to
        }
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def recent_tasks(self, n: int = 5):
        if not self.log_file.exists():
            return []
        entries = []
        with open(self.log_file, "r") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    if "score" in obj:
                        entries.append(obj)
                except Exception:
                    continue
        return entries[-n:]

    def status(self):
        return {
            "enabled": self.enabled,
            "threshold": self.threshold,
            "recent_tasks": self.recent_tasks()
        }


semantic_scorer = SemanticTaskScorer()
