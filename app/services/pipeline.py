from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai import AIProvider
from app.collectors import CollectorAdapter
from app.db.repositories import PipelineRepository
from app.services.ai_classifier import AIClassifierService
from app.services.collector import CollectorService
from app.services.digest import DigestSender, DigestService
from app.services.matching import MatchingEngine


@dataclass(slots=True)
class PipelineReport:
    collection_statuses: dict[str, str] = field(default_factory=dict)
    classified_count: int = 0
    matched_count: int = 0
    notified_count: int = 0
    errors: list[str] = field(default_factory=list)


class PipelineService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        collectors: dict[str, CollectorAdapter],
        ai_provider: AIProvider | None,
        digest_sender: DigestSender | None,
        profile_id: int,
        prompt_version: str,
        digest_min_score: int,
        digest_batch_size: int = 20,
        include_international: bool = False,
    ) -> None:
        self.session_factory = session_factory
        self.collectors = collectors
        self.ai_provider = ai_provider
        self.digest_sender = digest_sender
        self.profile_id = profile_id
        self.prompt_version = prompt_version
        self.digest_min_score = digest_min_score
        self.digest_batch_size = digest_batch_size
        self.include_international = include_international

    async def run(self) -> PipelineReport:
        report = PipelineReport()
        await self._collect(report)
        await self._classify_and_match(report)
        await self._digest(report)
        return report

    async def _collect(self, report: PipelineReport) -> None:
        for name, adapter in self.collectors.items():
            async with self.session_factory() as session:
                try:
                    run = await CollectorService(session).run(adapter)
                    await session.commit()
                    report.collection_statuses[name] = run.status
                    if run.error:
                        report.errors.append(f"collect {name}: {run.error}")
                except Exception as exc:
                    await session.rollback()
                    report.collection_statuses[name] = "failed"
                    report.errors.append(f"collect {name}: {self._error(exc)}")

    async def _classify_and_match(self, report: PipelineReport) -> None:
        async with self.session_factory() as session:
            repository = PipelineRepository(session)
            profile = await repository.get_profile(self.profile_id)
            if profile is None:
                report.errors.append(f"profile {self.profile_id} not found")
                return
            opportunities = await repository.active_opportunities()
            classifier = (
                AIClassifierService(session, self.ai_provider, prompt_version=self.prompt_version)
                if self.ai_provider is not None
                else None
            )
            if classifier is None:
                report.errors.append("classification skipped: AI provider is not configured")

            matching = MatchingEngine(session)
            for opportunity in opportunities:
                try:
                    if classifier is not None:
                        outcome = await classifier.classify(opportunity)
                        if not outcome.skipped and outcome.analysis.status == "success":
                            report.classified_count += 1
                    analysis = await repository.latest_successful_analysis(opportunity.id)
                    if analysis is None:
                        continue
                    await matching.calculate_and_store(profile, opportunity, analysis)
                    report.matched_count += 1
                except Exception as exc:
                    report.errors.append(
                        f"process opportunity {opportunity.id}: {self._error(exc)}"
                    )
            await session.commit()

    async def _digest(self, report: PipelineReport) -> None:
        if self.digest_sender is None:
            report.errors.append("digest skipped: sender is not configured")
            return
        async with self.session_factory() as session:
            try:
                report.notified_count = await DigestService(
                    session,
                    self.digest_sender,
                    profile_id=self.profile_id,
                    min_score=self.digest_min_score,
                    batch_size=self.digest_batch_size,
                    include_international=self.include_international,
                ).send_pending()
                await session.commit()
            except Exception as exc:
                await session.rollback()
                report.errors.append(f"digest: {self._error(exc)}")

    @staticmethod
    def _error(exc: Exception) -> str:
        return (str(exc).strip() or exc.__class__.__name__)[:1000]
