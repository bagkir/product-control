from datetime import date, datetime

from pydantic import BaseModel, Field


class DashboardSummary(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float


class TodayStatistics(BaseModel):
    batches_created: int
    batches_closed: int
    products_added: int
    products_aggregated: int


class ShiftStatistics(BaseModel):
    batches: int
    products: int
    aggregated: int


class WorkCenterStatistics(BaseModel):
    id: str
    name: str
    batches_count: int
    products_count: int
    aggregation_rate: float


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    today: TodayStatistics
    by_shift: dict[str, ShiftStatistics]
    top_work_centers: list[WorkCenterStatistics]
    cached_at: datetime


class BatchInfoStatistics(BaseModel):
    id: int
    batch_number: int
    batch_date: date
    is_closed: bool


class ProductionStatistics(BaseModel):
    total_products: int
    aggregated: int
    remaining: int
    aggregation_rate: float


class TimelineStatistics(BaseModel):
    shift_duration_hours: float
    elapsed_hours: float
    products_per_hour: float
    estimated_completion: datetime | None


class TeamPerformance(BaseModel):
    team: str
    avg_products_per_hour: float
    efficiency_score: float


class BatchStatisticsResponse(BaseModel):
    batch_info: BatchInfoStatistics
    production_stats: ProductionStatistics
    timeline: TimelineStatistics
    team_performance: TeamPerformance


class CompareBatchesRequest(BaseModel):
    batch_ids: list[int] = Field(
        min_length=1,
        max_length=50,
    )


class BatchComparison(BaseModel):
    batch_id: int
    batch_number: int
    total_products: int
    aggregated: int
    rate: float
    duration_hours: float
    products_per_hour: float


class ComparisonAverage(BaseModel):
    aggregation_rate: float
    products_per_hour: float


class CompareBatchesResponse(BaseModel):
    comparison: list[BatchComparison]
    average: ComparisonAverage


class DashboardStatsResponse(BaseModel):
    total_batches: int
    active_batches: int
    closed_batches: int
    total_products: int
    aggregated_products: int
    aggregation_rate: float
    cached_at: datetime | None = None
