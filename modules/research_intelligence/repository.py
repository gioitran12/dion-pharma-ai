# -*- coding: utf-8 -*-
"""
DION Healthcare AI — Medical Literature Repository
Quản lý nạp, tra cứu và lưu trữ cơ sở dữ liệu nghiên cứu lâm sàng PubMed và hoạt chất vi chất.
"""

import os
import json
import threading
from typing import List, Optional, Dict, Any

from modules.research_intelligence.schemas import (
    StudyRecord, ActiveIngredientInfo, StudyType, EvidenceGrade
)

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "medical_literature.json")
_repo_lock = threading.Lock()


class MedicalLiteratureRepository:
    def __init__(self, data_file: str = DATA_PATH):
        self.data_file = data_file
        self._ingredients: List[ActiveIngredientInfo] = []
        self._studies: List[StudyRecord] = []
        self._load()

    def _load(self):
        """Đọc dữ liệu từ file JSON vào bộ nhớ"""
        with _repo_lock:
            if not os.path.exists(self.data_file):
                self._ingredients = []
                self._studies = []
                return

            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._ingredients = [
                ActiveIngredientInfo(**item)
                for item in data.get("active_ingredients", [])
            ]
            self._studies = [
                StudyRecord(**item)
                for item in data.get("studies", [])
            ]

    def _save(self):
        """Lưu toàn bộ dữ liệu vào file JSON một cách an toàn (atomic write)"""
        with _repo_lock:
            data = {
                "active_ingredients": [ing.model_dump() for ing in self._ingredients],
                "studies": [st.model_dump() for st in self._studies]
            }
            tmp_file = f"{self.data_file}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_file, self.data_file)

    def list_active_ingredients(self) -> List[ActiveIngredientInfo]:
        """Trả về toàn bộ danh mục hoạt chất vi chất"""
        return list(self._ingredients)

    def get_ingredients(self, category: Optional[str] = None) -> List[ActiveIngredientInfo]:
        """Lấy danh sách hoạt chất kèm bộ lọc nhóm (CANXI, SAT, VITAMIN,...)"""
        if not category or category.upper() == "ALL":
            return list(self._ingredients)
        cat_upper = category.upper().strip()
        return [ing for ing in self._ingredients if ing.category.upper() == cat_upper]

    def get_ingredient_by_id(self, ing_id: str) -> Optional[ActiveIngredientInfo]:
        """Tìm hoạt chất theo ID"""
        target = ing_id.lower().strip()
        for ing in self._ingredients:
            if ing.id.lower() == target:
                return ing
        return None

    def get_ingredient_by_name(self, name: str) -> Optional[ActiveIngredientInfo]:
        """Tìm hoạt chất theo tên gần đúng"""
        norm_name = name.lower().strip()
        for ing in self._ingredients:
            if norm_name in ing.name.lower() or norm_name in ing.scientific_name.lower():
                return ing
        return None

    def list_studies(self) -> List[StudyRecord]:
        """Trả về toàn bộ danh sách nghiên cứu lâm sàng"""
        return list(self._studies)

    def get_study_by_pmid(self, pmid: str) -> Optional[StudyRecord]:
        """Tra cứu chi tiết một nghiên cứu bằng PMID"""
        norm_pmid = pmid.upper().replace(" ", "").replace(":", "")
        for s in self._studies:
            s_norm = s.pmid.upper().replace(" ", "").replace(":", "")
            if norm_pmid in s_norm or s_norm in norm_pmid:
                return s
        return None

    def search_studies(
        self,
        query: Optional[str] = None,
        ingredient: Optional[str] = None,
        ingredient_id: Optional[str] = None,
        study_type: Optional[str] = None,
        evidence_grade: Optional[str] = None,
        target_group: Optional[str] = None,
        limit: int = 50
    ) -> List[StudyRecord]:
        """
        Tìm kiếm và lọc nghiên cứu lâm sàng theo nhiều tiêu chí kết hợp:
        - query: Tìm trong tiêu đề tiếng Anh, tiếng Việt, tác giả, kết quả chính hoặc tags
        - ingredient / ingredient_id: Lọc theo tên hoặc mã hoạt chất
        - study_type: Lọc theo thiết kế nghiên cứu (RCT, META_ANALYSIS, v.v.)
        - evidence_grade: Lọc theo phân hạng bằng chứng (GRADE_A, GRADE_B, GRADE_C)
        - target_group: Lọc theo nhóm đối tượng (Mẹ bầu, Người lớn tuổi, v.v.)
        """
        results = list(self._studies)

        # 1. Lọc theo hoạt chất
        target_ing = ingredient or ingredient_id
        if target_ing and target_ing.strip():
            ing_lower = target_ing.lower().strip()
            tokens = [t for t in ing_lower.replace("-", " ").split() if len(t) > 3]
            results = [
                s for s in results
                if ing_lower in s.ingredient.lower()
                or (hasattr(s, 'ingredient_id') and s.ingredient_id and ing_lower in s.ingredient_id.lower())
                or any(ing_lower in t.lower() or t.lower() in ing_lower for t in s.tags)
                or (tokens and any(tok in s.ingredient.lower() or any(tok in t.lower() for t in s.tags) for tok in tokens))
            ]

        # 2. Lọc theo thiết kế nghiên cứu
        if study_type and study_type.strip() and study_type.upper() != "ALL":
            st_upper = study_type.upper().strip()
            results = [s for s in results if s.study_type.value == st_upper]

        # 3. Lọc theo phân hạng bằng chứng
        if evidence_grade and evidence_grade.strip() and evidence_grade.upper() != "ALL":
            eg_upper = evidence_grade.upper().strip()
            results = [s for s in results if s.evidence_grade.value == eg_upper]

        # 4. Lọc theo nhóm đối tượng
        if target_group and target_group.strip() and target_group.upper() != "ALL":
            tg_lower = target_group.lower().strip()
            results = [s for s in results if tg_lower in s.target_group.lower()]

        # 5. Lọc theo từ khóa tự do
        if query and query.strip():
            q_terms = [t.strip().lower() for t in query.split() if t.strip()]
            filtered = []
            for s in results:
                searchable_text = f"{s.pmid} {s.title_en} {s.title_vi} {s.authors} {s.journal} {s.key_findings} {s.dosage} {s.dion_application} {s.adverse_events} {s.abstract} {s.ingredient} {s.target_group} {s.intervention} {s.control} {' '.join(s.tags)}".lower()
                if all(term in searchable_text for term in q_terms):
                    filtered.append(s)
            results = filtered

        return results[:limit]

    def add_study(self, study: StudyRecord) -> StudyRecord:
        """Thêm mới một nghiên cứu vào kho lưu trữ"""
        with _repo_lock:
            # Kiểm tra xem pmid đã tồn tại chưa
            existing = self.get_study_by_pmid(study.pmid)
            if existing:
                self._studies = [s if s.pmid != study.pmid else study for s in self._studies]
            else:
                self._studies.append(study)
            self._save()
            return study


# Singleton instance
_literature_repo = None


def get_medical_literature_repository() -> MedicalLiteratureRepository:
    global _literature_repo
    if _literature_repo is None:
        _literature_repo = MedicalLiteratureRepository()
    return _literature_repo
