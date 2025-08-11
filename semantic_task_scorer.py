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

        # Context length and token count (more generous thresholds)
        length_norm = min(len(text) / 80, 1.0)  # Lower threshold for length
        token_norm = min(len(text.split()) / 15, 1.0)  # Lower threshold for tokens
        score += 0.25 * length_norm  # Higher weight for complexity
        score += 0.25 * token_norm

        # Keyword analysis (expanded heavy keywords with higher weights)
        heavy_keywords = [
            "optimize", "analyze", "summarize", "plan", "research",
            "implement", "generate", "build", "develop", "comprehensive",
            "detailed", "troubleshoot", "diagnostic", "configuration", 
            "investigate", "performance", "security", "vulnerability",
            "orchestration", "deployment", "architecture", "system",
            "complex", "advanced", "sophisticated", "intricate", "thorough"
        ]
        
        # Additional complexity indicators
        complexity_indicators = [
            "network", "docker", "container", "database", "server",
            "monitoring", "logging", "backup", "restore", "migration",
            "deployment", "scaling", "load", "performance", "memory",
            "cpu", "disk", "storage", "bandwidth", "latency", "infrastructure",
            "automation", "orchestration", "microservices", "kubernetes"
        ]
        
        # Container-specific queries that often need dev machine access
        container_routing_keywords = [
            "containers", "docker ps", "docker images", "docker logs",
            "docker exec", "docker inspect", "container status", "running containers",
            "container info", "container details", "docker system", "docker stats"
        ]
        
        light_keywords = ["list", "show", "echo", "simple", "test", "example", "help", "check", "status", "hello"]
        
        # Count keyword matches for more nuanced scoring
        heavy_matches = sum(1 for k in heavy_keywords if k in text_lower)
        complexity_matches = sum(1 for k in complexity_indicators if k in text_lower)
        container_matches = sum(1 for k in container_routing_keywords if k in text_lower)
        light_matches = sum(1 for k in light_keywords if k in text_lower)
        
        # Special handling for container queries that need external access
        if container_matches > 0:
            # Container queries often need dev machine access if local Docker isn't available
            score += min(0.6, 0.25 * container_matches)  # Higher weight for container queries (up to 0.6)
        
        # Weight based on number of matches
        if heavy_matches > 0:
            score += min(0.4, 0.15 * heavy_matches)  # Up to 0.4 for heavy keywords
        if complexity_matches > 0:
            score += min(0.3, 0.1 * complexity_matches)  # Up to 0.3 for complexity
        if light_matches > 0 and container_matches == 0:  # Don't penalize if container-related
            score -= min(0.4, 0.2 * light_matches)  # Penalize simple queries

        # Embedding similarity (if available)
        if self.embed_ok:
            try:
                emb = self.model.encode([text])
                heavy_sim = float(self.util.cos_sim(emb, self.heavy_emb).max())
                light_sim = float(self.util.cos_sim(emb, self.light_emb).max())
                
                # More aggressive embedding scoring
                if heavy_sim > 0.6:  # Strong similarity to complex tasks
                    score += 0.3
                elif heavy_sim > 0.4:  # Medium similarity
                    score += 0.2
                elif heavy_sim > 0.3:  # Weak similarity
                    score += 0.1
                    
                if light_sim > 0.7:  # Very similar to simple tasks
                    score -= 0.3
                elif light_sim > 0.5:  # Somewhat similar to simple tasks
                    score -= 0.2
                    
            except Exception:
                # Fallback if embeddings fail at runtime
                pass

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
