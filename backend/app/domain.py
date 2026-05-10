import os
from dataclasses import dataclass, field
from typing import Optional

import yaml

from app.core.embeddings import EMBEDDING_DIM
from app.core.faiss_store import FAISSVectorDB


@dataclass
class DomainPack:
    id: str
    name: str
    description: str
    system_prompt: str
    noise_filters: list[str]
    top_k: int
    relevance_threshold: float
    pdf_folder: str
    vector_db_path: str
    db: Optional[FAISSVectorDB] = field(default=None, repr=False)


class DomainRegistry:
    _instance: Optional["DomainRegistry"] = None

    def __init__(self):
        self._domains: dict[str, DomainPack] = {}

    @classmethod
    def get_instance(cls) -> "DomainRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_all(self, domains_dir: str) -> None:
        if not os.path.isdir(domains_dir):
            print(f"Warning: Domains directory not found: {domains_dir}")
            return

        for filename in sorted(os.listdir(domains_dir)):
            if not filename.endswith(".yaml"):
                continue

            path = os.path.join(domains_dir, filename)
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)

            domain_id = cfg["id"]
            db = FAISSVectorDB(EMBEDDING_DIM)
            try:
                db.load(cfg["vector_db_path"])
            except Exception as e:
                print(
                    f"Warning: Could not load FAISS index for domain '{domain_id}' "
                    f"from '{cfg['vector_db_path']}': {e}\n"
                    f"  Build it first: python -m app.indexer.build {path}"
                )
                continue

            self._domains[domain_id] = DomainPack(
                id=domain_id,
                name=cfg["name"],
                description=cfg["description"],
                system_prompt=cfg["system_prompt"],
                noise_filters=cfg.get("noise_filters", []),
                top_k=cfg.get("top_k", 3),
                relevance_threshold=cfg.get("relevance_threshold", 1.2),
                pdf_folder=cfg["pdf_folder"],
                vector_db_path=cfg["vector_db_path"],
                db=db,
            )
            print(f"  Loaded domain: {domain_id} ({db.index.ntotal} vectors)")

    def get(self, domain_id: str) -> Optional[DomainPack]:
        return self._domains.get(domain_id)

    def list_all(self) -> list[DomainPack]:
        return list(self._domains.values())

    def ids(self) -> list[str]:
        return list(self._domains.keys())
