"""
Keyword Parser

다양한 형식의 키워드 파일 파싱:
- CSV (keyword, volume, difficulty, related)
- ALSO 형식 (Also Asked 스타일)
- 일반 텍스트 (줄당 하나)
- JSON/YAML
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Set
from pathlib import Path
from enum import Enum
import re

logger = logging.getLogger(__name__)


class KeywordType(Enum):
    """키워드 타입"""
    PRIMARY = "primary"          # 주요 키워드
    RELATED = "related"          # 관련 키워드
    LONG_TAIL = "long_tail"      # 롱테일 키워드
    QUESTION = "question"        # 질문형 키워드
    LOCAL = "local"              # 지역 키워드
    BRAND = "brand"              # 브랜드 키워드


@dataclass
class KeywordEntry:
    """키워드 엔트리"""
    keyword: str
    keyword_type: KeywordType = KeywordType.PRIMARY
    volume: int = 0                    # 검색량
    difficulty: float = 0.0            # 경쟁 난이도 (0-100)
    cpc: float = 0.0                   # CPC
    related_keywords: List[str] = field(default_factory=list)
    parent_keyword: Optional[str] = None
    category: Optional[str] = None
    intent: Optional[str] = None       # informational, transactional, navigational
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self):
        return hash(self.keyword)

    def __eq__(self, other):
        if isinstance(other, KeywordEntry):
            return self.keyword == other.keyword
        return False


class KeywordParser:
    """키워드 파일 파서"""

    # 질문형 키워드 패턴
    QUESTION_PATTERNS = [
        r'^(어떻게|왜|무엇|어디|언제|누가|어느|뭐가|뭘)',
        r'(하는법|방법|추천|순위|비교|후기|리뷰)$',
        r'\?$'
    ]

    # 지역 키워드 패턴
    LOCAL_PATTERNS = [
        r'(서울|부산|대구|인천|광주|대전|울산|세종)',
        r'(경기|강원|충북|충남|전북|전남|경북|경남|제주)',
        r'(강남|홍대|이태원|명동|잠실|신촌|건대|압구정)',
        r'(역|동|구|시|군)\s*(맛집|카페|여행|숙소)'
    ]

    def __init__(self):
        self._question_regex = [re.compile(p) for p in self.QUESTION_PATTERNS]
        self._local_regex = [re.compile(p) for p in self.LOCAL_PATTERNS]

    async def parse_file(self, file_path: str) -> List[KeywordEntry]:
        """
        파일 파싱 (형식 자동 감지)

        Args:
            file_path: 키워드 파일 경로

        Returns:
            List[KeywordEntry]: 파싱된 키워드 목록
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Keyword file not found: {file_path}")

        suffix = path.suffix.lower()

        if suffix == '.csv':
            return await self._parse_csv(path)
        elif suffix == '.json':
            return await self._parse_json(path)
        elif suffix == '.yaml' or suffix == '.yml':
            return await self._parse_yaml(path)
        elif suffix == '.txt':
            return await self._parse_text(path)
        else:
            # 확장자로 판단 안되면 내용으로 판단
            return await self._parse_auto(path)

    async def _parse_csv(self, path: Path) -> List[KeywordEntry]:
        """CSV 파싱"""
        entries = []

        with open(path, 'r', encoding='utf-8') as f:
            # 헤더 감지
            first_line = f.readline().strip().lower()
            f.seek(0)

            has_header = any(
                h in first_line
                for h in ['keyword', '키워드', 'volume', 'difficulty']
            )

            reader = csv.DictReader(f) if has_header else csv.reader(f)

            for row in reader:
                entry = self._parse_csv_row(row, has_header)
                if entry:
                    entries.append(entry)

        logger.info(f"Parsed {len(entries)} keywords from CSV: {path.name}")
        return entries

    def _parse_csv_row(
        self,
        row: Any,
        has_header: bool
    ) -> Optional[KeywordEntry]:
        """CSV 행 파싱"""
        try:
            if has_header:
                # 딕셔너리 형태
                keyword = (
                    row.get('keyword') or
                    row.get('키워드') or
                    row.get('Keyword') or
                    ''
                ).strip()

                if not keyword:
                    return None

                volume = int(row.get('volume', row.get('검색량', 0)) or 0)
                difficulty = float(row.get('difficulty', row.get('난이도', 0)) or 0)
                cpc = float(row.get('cpc', row.get('CPC', 0)) or 0)

                related_str = row.get('related', row.get('관련키워드', ''))
                related = [
                    r.strip() for r in related_str.split(',')
                    if r.strip()
                ] if related_str else []

                category = row.get('category', row.get('카테고리', ''))
                intent = row.get('intent', row.get('의도', ''))

            else:
                # 리스트 형태
                if not row or not row[0].strip():
                    return None

                keyword = row[0].strip()
                volume = int(row[1]) if len(row) > 1 and row[1] else 0
                difficulty = float(row[2]) if len(row) > 2 and row[2] else 0
                cpc = float(row[3]) if len(row) > 3 and row[3] else 0
                related = []
                category = ''
                intent = ''

            # 키워드 타입 자동 분류
            keyword_type = self._classify_keyword_type(keyword)

            return KeywordEntry(
                keyword=keyword,
                keyword_type=keyword_type,
                volume=volume,
                difficulty=difficulty,
                cpc=cpc,
                related_keywords=related,
                category=category or None,
                intent=intent or None
            )

        except Exception as e:
            logger.warning(f"Failed to parse row: {row}, error: {e}")
            return None

    async def _parse_json(self, path: Path) -> List[KeywordEntry]:
        """JSON 파싱"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        entries = []

        # 배열 형태
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    entries.append(KeywordEntry(
                        keyword=item,
                        keyword_type=self._classify_keyword_type(item)
                    ))
                elif isinstance(item, dict):
                    entries.append(self._dict_to_entry(item))

        # 카테고리별 그룹 형태
        elif isinstance(data, dict):
            for category, keywords in data.items():
                if isinstance(keywords, list):
                    for kw in keywords:
                        if isinstance(kw, str):
                            entries.append(KeywordEntry(
                                keyword=kw,
                                keyword_type=self._classify_keyword_type(kw),
                                category=category
                            ))
                        elif isinstance(kw, dict):
                            entry = self._dict_to_entry(kw)
                            entry.category = category
                            entries.append(entry)

        logger.info(f"Parsed {len(entries)} keywords from JSON: {path.name}")
        return entries

    async def _parse_yaml(self, path: Path) -> List[KeywordEntry]:
        """YAML 파싱"""
        import yaml

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # JSON과 동일한 구조 지원
        return await self._parse_json_data(data, path.name)

    async def _parse_json_data(self, data: Any, source: str) -> List[KeywordEntry]:
        """JSON/YAML 데이터 파싱"""
        entries = []

        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    entries.append(KeywordEntry(
                        keyword=item,
                        keyword_type=self._classify_keyword_type(item)
                    ))
                elif isinstance(item, dict):
                    entries.append(self._dict_to_entry(item))

        elif isinstance(data, dict):
            for category, keywords in data.items():
                if isinstance(keywords, list):
                    for kw in keywords:
                        if isinstance(kw, str):
                            entries.append(KeywordEntry(
                                keyword=kw,
                                keyword_type=self._classify_keyword_type(kw),
                                category=category
                            ))

        logger.info(f"Parsed {len(entries)} keywords from {source}")
        return entries

    async def _parse_text(self, path: Path) -> List[KeywordEntry]:
        """텍스트 파일 파싱 (줄당 하나)"""
        entries = []

        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                keyword = line.strip()
                if keyword and not keyword.startswith('#'):
                    entries.append(KeywordEntry(
                        keyword=keyword,
                        keyword_type=self._classify_keyword_type(keyword)
                    ))

        logger.info(f"Parsed {len(entries)} keywords from text: {path.name}")
        return entries

    async def _parse_auto(self, path: Path) -> List[KeywordEntry]:
        """형식 자동 감지 파싱"""
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # JSON 시도
        try:
            data = json.loads(content)
            return await self._parse_json_data(data, path.name)
        except json.JSONDecodeError:
            pass

        # CSV 시도
        if ',' in content:
            return await self._parse_csv(path)

        # 텍스트로 처리
        return await self._parse_text(path)

    def _dict_to_entry(self, data: dict) -> KeywordEntry:
        """딕셔너리를 KeywordEntry로 변환"""
        keyword = data.get('keyword', data.get('키워드', ''))

        return KeywordEntry(
            keyword=keyword,
            keyword_type=self._classify_keyword_type(keyword),
            volume=int(data.get('volume', data.get('검색량', 0)) or 0),
            difficulty=float(data.get('difficulty', data.get('난이도', 0)) or 0),
            cpc=float(data.get('cpc', 0) or 0),
            related_keywords=data.get('related', data.get('related_keywords', [])),
            category=data.get('category', data.get('카테고리')),
            intent=data.get('intent', data.get('의도')),
            metadata=data.get('metadata', {})
        )

    def _classify_keyword_type(self, keyword: str) -> KeywordType:
        """키워드 타입 자동 분류"""
        # 질문형 체크
        for pattern in self._question_regex:
            if pattern.search(keyword):
                return KeywordType.QUESTION

        # 지역 키워드 체크
        for pattern in self._local_regex:
            if pattern.search(keyword):
                return KeywordType.LOCAL

        # 롱테일 (4단어 이상)
        if len(keyword.split()) >= 4:
            return KeywordType.LONG_TAIL

        return KeywordType.PRIMARY

    async def parse_also_format(self, file_path: str) -> List[KeywordEntry]:
        """
        Also Asked / People Also Ask 형식 파싱

        형식 예시:
            메인키워드
            ├── 관련질문1
            │   ├── 하위질문1-1
            │   └── 하위질문1-2
            └── 관련질문2
        """
        entries = []
        current_parent = None
        indent_stack = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue

                # 들여쓰기 레벨 계산
                indent = len(line) - len(line.lstrip())

                # 트리 기호 제거
                keyword = re.sub(r'^[├└│─\s]+', '', stripped).strip()

                if not keyword:
                    continue

                # 인덴트 레벨에 따른 부모 결정
                while indent_stack and indent_stack[-1][0] >= indent:
                    indent_stack.pop()

                parent = indent_stack[-1][1] if indent_stack else None

                entry = KeywordEntry(
                    keyword=keyword,
                    keyword_type=KeywordType.QUESTION if '?' in keyword else KeywordType.RELATED,
                    parent_keyword=parent
                )
                entries.append(entry)

                indent_stack.append((indent, keyword))

        logger.info(f"Parsed {len(entries)} keywords from ALSO format")
        return entries

    def deduplicate(self, entries: List[KeywordEntry]) -> List[KeywordEntry]:
        """중복 제거"""
        seen: Set[str] = set()
        unique = []

        for entry in entries:
            normalized = entry.keyword.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique.append(entry)

        return unique

    def filter_by_volume(
        self,
        entries: List[KeywordEntry],
        min_volume: int = 0,
        max_volume: Optional[int] = None
    ) -> List[KeywordEntry]:
        """검색량 필터"""
        filtered = [e for e in entries if e.volume >= min_volume]
        if max_volume:
            filtered = [e for e in filtered if e.volume <= max_volume]
        return filtered

    def filter_by_type(
        self,
        entries: List[KeywordEntry],
        types: List[KeywordType]
    ) -> List[KeywordEntry]:
        """타입 필터"""
        return [e for e in entries if e.keyword_type in types]
