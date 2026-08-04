from __future__ import annotations

from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    The application intentionally has no live-trading switch. The Alpaca client is always
    constructed with ``paper=True``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AEGIS_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    alpaca_api_key: SecretStr | None = None
    alpaca_secret_key: SecretStr | None = None

    symbol: str = "TQQQ"
    database_path: Path = Path("data/aegis.db")
    poll_seconds: int = Field(default=20, ge=5, le=300)
    log_level: str = "INFO"

    risk_per_trade_pct: Decimal = Field(default=Decimal("0.0025"), gt=0, le=Decimal("0.01"))
    max_daily_loss_pct: Decimal = Field(default=Decimal("0.01"), gt=0, le=Decimal("0.03"))
    max_position_notional_pct: Decimal = Field(
        default=Decimal("0.25"), gt=0, le=Decimal("0.50")
    )
    max_trades_per_day: int = Field(default=3, ge=1, le=10)
    reward_to_risk: Decimal = Field(default=Decimal("2.0"), ge=Decimal("1.0"), le=Decimal("5"))

    bar_minutes: int = Field(default=5, ge=1, le=15)
    opening_range_minutes: int = Field(default=15, ge=5, le=60)
    volume_lookback: int = Field(default=5, ge=2, le=20)
    volume_factor: Decimal = Field(default=Decimal("1.20"), ge=Decimal("1"), le=Decimal("5"))
    max_extension_pct: Decimal = Field(default=Decimal("0.004"), gt=0, le=Decimal("0.03"))
    max_stop_pct: Decimal = Field(default=Decimal("0.0125"), gt=0, le=Decimal("0.05"))
    max_spread_bps: Decimal = Field(default=Decimal("20"), gt=0, le=Decimal("100"))
    quote_max_age_seconds: int = Field(default=30, ge=5, le=120)

    entry_start: time = time(9, 45)
    entry_cutoff: time = time(14, 0)
    flatten_time: time = time(15, 50)
    market_timezone: str = "America/New_York"

    mcp_transport: str = "stdio"
    mcp_host: str = "127.0.0.1"
    mcp_port: int = Field(default=8765, ge=1024, le=65535)

    @model_validator(mode="after")
    def validate_strategy_window(self) -> Self:
        if self.opening_range_minutes % self.bar_minutes != 0:
            raise ValueError("opening_range_minutes must be divisible by bar_minutes")
        if not self.entry_start < self.entry_cutoff < self.flatten_time:
            raise ValueError("Expected entry_start < entry_cutoff < flatten_time")
        self.symbol = self.symbol.strip().upper()
        if not self.symbol.isalnum():
            raise ValueError("symbol must contain only letters and numbers")
        return self

    def require_alpaca_credentials(self) -> tuple[str, str]:
        if self.alpaca_api_key is None or self.alpaca_secret_key is None:
            raise RuntimeError(
                "Missing paper API credentials. Set AEGIS_ALPACA_API_KEY and "
                "AEGIS_ALPACA_SECRET_KEY."
            )
        return (
            self.alpaca_api_key.get_secret_value(),
            self.alpaca_secret_key.get_secret_value(),
        )
