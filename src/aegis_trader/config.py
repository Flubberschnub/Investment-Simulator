from __future__ import annotations

from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ExecutionMode(StrEnum):
    SIMULATION = "simulation"
    SCHWAB_SHADOW = "schwab_shadow"
    SCHWAB_LIVE = "schwab_live"


LIVE_ACK = "I_HAVE_WRITTEN_COMPLIANCE_APPROVAL"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AEGIS_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    execution_mode: ExecutionMode = ExecutionMode.SIMULATION
    symbol: str = "TQQQ"
    database_path: Path = Path("data/aegis.db")

    starting_cash: Decimal = Field(default=Decimal("10000"), gt=0)
    risk_per_trade_pct: Decimal = Field(default=Decimal("0.0025"), gt=0, le=Decimal("0.01"))
    max_daily_loss_pct: Decimal = Field(default=Decimal("0.01"), gt=0, le=Decimal("0.03"))
    max_position_notional_pct: Decimal = Field(default=Decimal("0.25"), gt=0, le=Decimal("0.50"))
    max_trades_per_day: int = Field(default=3, ge=1, le=10)
    reward_to_risk: Decimal = Field(default=Decimal("2"), ge=1, le=5)

    opening_range_minutes: int = Field(default=15, ge=5, le=60)
    volume_lookback: int = Field(default=5, ge=2, le=20)
    volume_factor: Decimal = Field(default=Decimal("1.20"), ge=1, le=5)
    max_extension_pct: Decimal = Field(default=Decimal("0.004"), gt=0, le=Decimal("0.03"))
    max_stop_pct: Decimal = Field(default=Decimal("0.0125"), gt=0, le=Decimal("0.05"))

    schwab_client_id: SecretStr | None = None
    schwab_client_secret: SecretStr | None = None
    schwab_redirect_uri: str | None = None
    schwab_access_token: SecretStr | None = None
    schwab_account_hash: SecretStr | None = None
    schwab_market_base_url: str = "https://api.schwabapi.com/marketdata/v1"
    schwab_trader_base_url: str = "https://api.schwabapi.com/trader/v1"

    compliance_approved: bool = False
    live_trading_ack: SecretStr | None = None

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        self.symbol = self.symbol.strip().upper()
        if not self.symbol.isalnum():
            raise ValueError("symbol must contain only letters and numbers")
        if self.execution_mode is ExecutionMode.SCHWAB_LIVE:
            ack = self.live_trading_ack.get_secret_value() if self.live_trading_ack else ""
            if not self.compliance_approved or ack != LIVE_ACK:
                raise ValueError(
                    "schwab_live requires written compliance approval and the exact live acknowledgement"
                )
        return self

    def require_schwab_token(self) -> str:
        if self.schwab_access_token is None:
            raise RuntimeError("Set AEGIS_SCHWAB_ACCESS_TOKEN for Schwab read/shadow access")
        return self.schwab_access_token.get_secret_value()
