"""
UIContextBuilder - DeepSeek 프롬프트용 UI 컨텍스트 빌더

UI 트리를 DeepSeek이 이해할 수 있는 JSON 형식으로 변환합니다.

Author: Naver AI Evolution System
Created: 2025-12-17
"""

import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..portal_client.element import UITree, UIElement


@dataclass
class ContextOptions:
    """컨텍스트 옵션"""
    max_elements: int = 20  # 최대 요소 수
    include_non_clickable: bool = False  # 클릭 불가 요소 포함
    include_bounds: bool = True  # bounds 포함
    text_max_length: int = 50  # 텍스트 최대 길이
    region_filter: tuple = None  # (top_ratio, bottom_ratio, left_ratio, right_ratio)


class UIContextBuilder:
    """
    DeepSeek 프롬프트용 UI 컨텍스트 빌더

    사용 예시:
        builder = UIContextBuilder(screen_size=(1080, 2400))
        context = builder.build(ui_tree)
        json_str = builder.to_json(ui_tree)
    """

    def __init__(self, screen_size: tuple = (1080, 2400)):
        self.screen_size = screen_size

    def build(
        self,
        tree: UITree,
        options: ContextOptions = None
    ) -> Dict[str, Any]:
        """
        UI 트리를 컨텍스트로 변환

        Args:
            tree: UITree
            options: 컨텍스트 옵션

        Returns:
            컨텍스트 딕셔너리
        """
        options = options or ContextOptions()

        # 요소 필터링
        elements = self._filter_elements(tree, options)

        # 요소 정보 변환
        elements_info = []
        for i, elem in enumerate(elements[:options.max_elements]):
            info = self._element_to_dict(elem, i, options)
            elements_info.append(info)

        return {
            "screen": {
                "width": self.screen_size[0],
                "height": self.screen_size[1]
            },
            "summary": {
                "total_elements": len(tree.all_elements),
                "clickable_count": len(tree.clickable_elements),
                "visible_elements": len(elements)
            },
            "elements": elements_info
        }

    def _filter_elements(self, tree: UITree, options: ContextOptions) -> List[UIElement]:
        """요소 필터링"""
        if options.include_non_clickable:
            elements = tree.all_elements
        else:
            elements = tree.clickable_elements

        # 텍스트가 있는 요소만
        elements = [e for e in elements if e.text or e.content_desc]

        # 영역 필터
        if options.region_filter:
            top, bottom, left, right = options.region_filter
            w, h = self.screen_size
            elements = [
                e for e in elements
                if (w * left <= e.center[0] <= w * right and
                    h * top <= e.center[1] <= h * bottom)
            ]

        return elements

    def _element_to_dict(
        self,
        elem: UIElement,
        index: int,
        options: ContextOptions
    ) -> Dict[str, Any]:
        """요소를 딕셔너리로 변환"""
        text = elem.text or elem.content_desc
        if len(text) > options.text_max_length:
            text = text[:options.text_max_length] + "..."

        result = {
            "id": index,
            "text": text,
            "center": list(elem.center),
            "clickable": elem.clickable
        }

        if options.include_bounds:
            result["bounds"] = {
                "left": elem.bounds.left,
                "top": elem.bounds.top,
                "right": elem.bounds.right,
                "bottom": elem.bounds.bottom
            }

        # 클래스명 (간략화)
        class_short = elem.class_name.split(".")[-1] if elem.class_name else ""
        if class_short:
            result["type"] = class_short

        return result

    def to_json(
        self,
        tree: UITree,
        options: ContextOptions = None,
        indent: int = 2
    ) -> str:
        """JSON 문자열로 변환"""
        context = self.build(tree, options)
        return json.dumps(context, ensure_ascii=False, indent=indent)

    def to_prompt_text(
        self,
        tree: UITree,
        options: ContextOptions = None
    ) -> str:
        """
        DeepSeek 프롬프트에 삽입할 텍스트 형식

        Returns:
            프롬프트 텍스트
        """
        context = self.build(tree, options)

        lines = [
            f"화면 크기: {context['screen']['width']}x{context['screen']['height']}",
            f"전체 요소: {context['summary']['total_elements']}개",
            f"클릭 가능: {context['summary']['clickable_count']}개",
            "",
            "현재 화면의 클릭 가능한 요소들:"
        ]

        for elem in context['elements']:
            text = elem['text']
            center = elem['center']
            lines.append(f"  [{elem['id']}] '{text}' - 좌표: ({center[0]}, {center[1]})")

        return "\n".join(lines)

    def find_best_match(
        self,
        tree: UITree,
        target_text: str,
        keywords: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        타겟 텍스트에 가장 잘 맞는 요소 찾기

        Args:
            tree: UITree
            target_text: 찾을 텍스트
            keywords: 추가 키워드

        Returns:
            매칭된 요소 정보 또는 None
        """
        clickable = tree.clickable_elements

        # 정확한 매칭
        for elem in clickable:
            if elem.text == target_text:
                return {
                    "element": elem,
                    "match_type": "exact",
                    "text": elem.text,
                    "center": elem.center
                }

        # 부분 매칭
        for elem in clickable:
            if target_text.lower() in elem.text.lower():
                return {
                    "element": elem,
                    "match_type": "partial",
                    "text": elem.text,
                    "center": elem.center
                }

        # 키워드 매칭
        if keywords:
            for kw in keywords:
                for elem in clickable:
                    if kw.lower() in elem.text.lower():
                        return {
                            "element": elem,
                            "match_type": "keyword",
                            "matched_keyword": kw,
                            "text": elem.text,
                            "center": elem.center
                        }

        return None
