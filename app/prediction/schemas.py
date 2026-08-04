from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
import re
from typing import Optional


class ModelRequest(BaseModel):
    # Reject any field not defined below (protects against payload pollution
    # / probing), and strip stray whitespace from every string automatically.
    model_config = ConfigDict(
        from_attributes=True,
        extra="forbid",
        str_strip_whitespace=True,
        str_max_length=500,  # fallback cap for any str field below without its own max_length
    )


    machine_type: str = Field(..., max_length=50)
    technician: str = Field(..., min_length=1, max_length=100)

    # Machine
    machine_age_years: float = Field(..., ge=0, le=100)
    no_machine: bool = False
    under_warranty: bool = False

    # Schedule
    sched_year: int = Field(..., ge=2000, le=2100)
    sched_month: int = Field(..., ge=1, le=12)
    sched_day: int = Field(..., ge=1, le=31)
    sched_weekday: int = Field(..., ge=0, le=6)
    sched_week: int = Field(..., ge=1, le=53)
    sched_hour: Optional[int] = Field(None, ge=0, le=23)
    sched_hour_missing: bool = False
    days_since_start: int = Field(..., ge=0, le=100_000)

    # Lead time / deadline
    lead_time_days: Optional[float] = Field(None, ge=-3650, le=3650)
    lead_time_missing: bool = False
    deadline_slack_days: Optional[float] = Field(None, ge=-3650, le=3650)
    slack_missing: bool = False

    # Technician / visit
    tech_travel_time_min: float = Field(..., ge=0, le=1440)  # minutes in a day
    tech_tenure_years: float = Field(..., ge=0, le=60)
    is_fixed_appointment: bool = False
    visit_number: int = Field(..., ge=1, le=10_000)
    is_followup: bool = False
    tech_day_visits: int = Field(..., ge=0, le=1000)
    tech_day_planned_sum: float = Field(..., ge=0, le=1_000_000)

class ModelResponse(BaseModel):
    prediction: int
    model_config = ConfigDict(from_attributes=True)