from __future__ import annotations

from datetime import datetime
from pathlib import Path
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# --- DB location ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "project_s.db"
DB_URL = f"sqlite:///{DB_PATH.as_posix()}"

# --- Base ---
class Base(DeclarativeBase):
    pass


# =========================
# Core pipeline tables
# =========================

class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    channel_key: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    schema_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    seed_id: Mapped[str | None] = mapped_column(String(64))
    constraints_hash: Mapped[str | None] = mapped_column(String(64))


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    idea_text: Mapped[str] = mapped_column(Text)
    is_winner: Mapped[bool] = mapped_column(Boolean, default=False)

    score: Mapped[float | None] = mapped_column(Float)
    score_reason: Mapped[str | None] = mapped_column(Text)

    seed_theme: Mapped[str | None] = mapped_column(String(64))
    fear_axis: Mapped[str | None] = mapped_column(String(64))
    hook_type: Mapped[str | None] = mapped_column(String(64))
    pov: Mapped[str | None] = mapped_column(String(32))
    sensory_focus: Mapped[list | None] = mapped_column(JSON)

    # --- long-term dedupe fields (WINNERS ONLY) ---
    idea_canonical: Mapped[str | None] = mapped_column(Text)
    idea_embedding: Mapped[list | None] = mapped_column(JSON)
    idea_signature_hash: Mapped[str | None] = mapped_column(String(64), index=True)


class Script(Base):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), unique=True)

    word_count: Mapped[int]
    line_count: Mapped[int]
    avg_words_per_line: Mapped[float]
    validation_passed: Mapped[bool]

    ending_type: Mapped[str | None] = mapped_column(String(64))
    escalation_profile: Mapped[dict | None] = mapped_column(JSON)


class Beat(Base):
    __tablename__ = "beats"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    beat_id: Mapped[int]
    start_time: Mapped[float]
    end_time: Mapped[float]
    duration: Mapped[float]

    protagonist_visible: Mapped[bool]
    framing: Mapped[str]
    location_canonical: Mapped[str]
    visual_vibe: Mapped[str | None]

    __table_args__ = (
        UniqueConstraint("run_id", "beat_id", name="uq_run_beat"),
    )


class AudioLine(Base):
    __tablename__ = "audio_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    line_index: Mapped[int]
    words: Mapped[int]
    speech_duration: Mapped[float]
    words_per_second: Mapped[float]

    buffer_total: Mapped[float]
    start_time: Mapped[float]
    end_time: Mapped[float]

    __table_args__ = (
        UniqueConstraint("run_id", "line_index", name="uq_run_line"),
    )


# =========================
# Post-upload tables
# =========================

class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"), index=True)

    platform: Mapped[str] = mapped_column(String(32))
    video_external_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(32))
    title: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)


class MetricSnapshot(Base):
    __tablename__ = "metrics_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    views: Mapped[int]
    avg_percentage_viewed: Mapped[float | None]
    likes: Mapped[int]
    comments: Mapped[int]
    shares: Mapped[int]


class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True)

    insight_type: Mapped[str]
    payload: Mapped[dict] = mapped_column(JSON)
    confidence: Mapped[float]
    source_level: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =========================
# Init
# =========================

def main() -> int:
    engine = create_engine(DB_URL, future=True)
    Base.metadata.create_all(engine)
    print(f"DB initialized at {DB_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
