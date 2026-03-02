"""
파이프라인 실행 엔진
"""

from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
import asyncio
import logging

from .action_registry import ActionRegistry
from .action_base import ActionResult


@dataclass
class PipelineConfig:
    """파이프라인 설정"""
    name: str
    actions: List[str]  # 액션 이름 목록
    parallel: bool = False  # 병렬 실행 여부
    max_retries: int = 1
    break_on_failure: bool = False  # 실패 시 중단 여부


class PipelineEngine:
    """액션 파이프라인 실행 엔진"""

    def __init__(self, action_registry: ActionRegistry):
        self.registry = action_registry
        self.logger = logging.getLogger("pipeline")
        self.pipelines: Dict[str, PipelineConfig] = {}

    def register_pipeline(self, name: str, config: PipelineConfig):
        """파이프라인 등록"""
        self.pipelines[name] = config

    async def execute_pipeline(
        self,
        pipeline_name: str,
        initial_context: Dict[str, Any],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """파이프라인 실행"""
        if pipeline_name not in self.pipelines:
            raise ValueError(f"파이프라인 없음: {pipeline_name}")

        config = self.pipelines[pipeline_name]
        context = initial_context.copy()
        results = {}

        self.logger.info(f"파이프라인 시작: {pipeline_name} ({len(config.actions)}개 액션)")

        if config.parallel:
            # 병렬 실행
            tasks = []
            for action_name in config.actions:
                action = self.registry.get_action(action_name)
                if action:
                    task = self._execute_action_with_retry(
                        action, context, config.max_retries
                    )
                    tasks.append((action_name, task))

            # 병렬 실행 결과 수집
            for action_name, task in tasks:
                result = await task
                results[action_name] = result
                if progress_callback:
                    progress_callback(action_name, result)
        else:
            # 순차 실행
            for action_name in config.actions:
                action = self.registry.get_action(action_name)
                if not action:
                    self.logger.warning(f"액션 없음: {action_name}")
                    continue

                result = await self._execute_action_with_retry(
                    action, context, config.max_retries
                )
                results[action_name] = result

                if progress_callback:
                    progress_callback(action_name, result)

                # 컨텍스트 업데이트
                if result.success and result.data:
                    context.update(result.data)

                # 실패 시 처리
                if not result.success and config.break_on_failure:
                    self.logger.error(f"액션 실패로 파이프라인 중단: {action_name}")
                    break

        context["pipeline_results"] = results
        return context

    async def _execute_action_with_retry(
        self,
        action,
        context: Dict[str, Any],
        max_retries: int
    ) -> ActionResult:
        """재시도를 포함한 액션 실행"""
        for attempt in range(max_retries):
            try:
                result = await action._execute_with_timing(context)

                if result.success:
                    return result
                elif attempt < max_retries - 1:
                    retry_delay = min(2 ** attempt, 10)  # 지수 백오프
                    self.logger.warning(
                        f"액션 실패, {retry_delay}s 후 재시도: "
                        f"{action.name} (시도 {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(retry_delay)
            except Exception as e:
                if attempt < max_retries - 1:
                    retry_delay = min(2 ** attempt, 10)
                    self.logger.warning(
                        f"액션 예외, {retry_delay}s 후 재시도: "
                        f"{action.name} - {str(e)}"
                    )
                    await asyncio.sleep(retry_delay)

        # 모든 재시도 실패
        return ActionResult(
            success=False,
            error_message=f"액션 {action.name} 재시도 모두 실패"
        )
