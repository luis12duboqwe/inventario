"""Configuración general de la aplicación Softmobile Central."""
from __future__ import annotations

import os
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Annotated

from pydantic import (
    AliasChoices,
    Field,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    normalized = value.strip().lower()
    return normalized not in {"", "0", "false", "no", "off"}


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Valores de configuración cargados desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="allow",
    )

    database_url: Annotated[
        str,
        Field(
            ...,
            validation_alias=AliasChoices(
                "DATABASE_URL", "SOFTMOBILE_DATABASE_URL"),
        ),
    ]
    title: str = Field(default="Softmobile Central")
    version: str = Field(default="2.2.0")
    api_v1_prefix: Annotated[
        str,
        Field(
            default="/api/v2.2.0",
            validation_alias=AliasChoices(
                "API_V1_PREFIX",
                "SOFTMOBILE_API_PREFIX",
                "SOFTMOBILE_API_V1_PREFIX",
            ),
        ),
    ]
    api_alias_prefixes: Annotated[
        list[str],
        Field(
            default_factory=lambda: ["/api/v1"],
            validation_alias=AliasChoices(
                "API_ALIAS_PREFIXES",
                "SOFTMOBILE_API_ALIASES",
                "SOFTMOBILE_API_LEGACY_PREFIXES",
            ),
        ),
    ]
    secret_key: Annotated[
        str,
        Field(
            ...,
            validation_alias=AliasChoices(
                "JWT_SECRET_KEY",
                "SOFTMOBILE_SECRET_KEY",
                "SECRET_KEY",
            ),
        ),
    ]
    bootstrap_token: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "SOFTMOBILE_BOOTSTRAP_TOKEN",
                "BOOTSTRAP_TOKEN",
            ),
        ),
    ]
    access_token_expire_minutes: Annotated[
        int,
        Field(
            ...,
            validation_alias=AliasChoices(
                "ACCESS_TOKEN_EXPIRE_MINUTES",
                "SOFTMOBILE_TOKEN_MINUTES",
            ),
        ),
    ]
    # // [PACK28-config]
    refresh_token_expire_days: Annotated[
        int,
        Field(
            ...,
            validation_alias=AliasChoices(
                "REFRESH_TOKEN_EXPIRE_DAYS",
                "SOFTMOBILE_REFRESH_TOKEN_DAYS",
            ),
        ),
    ]
    session_cookie_expire_minutes: Annotated[
        int,
        Field(
            default=480,
            validation_alias=AliasChoices(
                "SESSION_COOKIE_EXPIRE_MINUTES",
                "SOFTMOBILE_SESSION_COOKIE_MINUTES",
            ),
        ),
    ]
    max_failed_login_attempts: Annotated[
        int,
        Field(
            default=5,
            validation_alias=AliasChoices(
                "MAX_FAILED_LOGIN_ATTEMPTS",
                "SOFTMOBILE_MAX_FAILED_LOGIN_ATTEMPTS",
            ),
        ),
    ]
    account_lock_minutes: Annotated[
        int,
        Field(
            default=15,
            validation_alias=AliasChoices(
                "ACCOUNT_LOCK_MINUTES",
                "SOFTMOBILE_ACCOUNT_LOCK_MINUTES",
            ),
        ),
    ]
    password_reset_token_minutes: Annotated[
        int,
        Field(
            default=30,
            validation_alias=AliasChoices(
                "PASSWORD_RESET_TOKEN_MINUTES",
                "SOFTMOBILE_PASSWORD_RESET_MINUTES",
            ),
        ),
    ]
    sync_interval_seconds: Annotated[
        int,
        Field(
            default=1800,
            validation_alias=AliasChoices(
                "SYNC_INTERVAL_SECONDS",
                "SOFTMOBILE_SYNC_INTERVAL_SECONDS",
            ),
        ),
    ]
    sync_retry_interval_seconds: Annotated[
        int,
        Field(
            default=600,
            validation_alias=AliasChoices(
                "SYNC_RETRY_INTERVAL_SECONDS",
                "SOFTMOBILE_SYNC_RETRY_INTERVAL_SECONDS",
            ),
        ),
    ]
    sync_max_attempts: Annotated[
        int,
        Field(
            default=5,
            validation_alias=AliasChoices(
                "SYNC_MAX_ATTEMPTS",
                "SOFTMOBILE_SYNC_MAX_ATTEMPTS",
            ),
        ),
    ]
    config_sync_directory: Annotated[
        str,
        Field(
            default_factory=lambda: str(
                Path(__file__).resolve().parents[2] / "ops" / "config_sync"
            ),
            validation_alias=AliasChoices(
                "CONFIG_SYNC_DIRECTORY",
                "SOFTMOBILE_CONFIG_SYNC_DIRECTORY",
            ),
        ),
    ]
    config_sync_enabled: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "CONFIG_SYNC_ENABLED",
                "SOFTMOBILE_CONFIG_SYNC_ENABLED",
            ),
        ),
    ]
    # // [PACK35-backend]
    sync_remote_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "SYNC_REMOTE_URL",
                "SOFTMOBILE_SYNC_REMOTE_URL",
            ),
        ),
    ]
    enable_background_scheduler: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_BACKGROUND_SCHEDULER",
                "SOFTMOBILE_ENABLE_SCHEDULER",
            ),
        ),
    ]
    notifications_email_from: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_FROM",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_FROM",
            ),
        ),
    ]
    notifications_email_host: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_HOST",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_HOST",
            ),
        ),
    ]
    notifications_email_port: Annotated[
        int,
        Field(
            default=587,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_PORT",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_PORT",
            ),
        ),
    ]
    notifications_email_username: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_USERNAME",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_USERNAME",
            ),
        ),
    ]
    notifications_email_password: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_PASSWORD",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_PASSWORD",
            ),
        ),
    ]
    notifications_email_use_tls: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_EMAIL_USE_TLS",
                "SOFTMOBILE_NOTIFICATIONS_EMAIL_USE_TLS",
            ),
        ),
    ]
    notifications_whatsapp_api_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_WHATSAPP_API_URL",
                "SOFTMOBILE_NOTIFICATIONS_WHATSAPP_API_URL",
            ),
        ),
    ]
    notifications_whatsapp_token: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_WHATSAPP_TOKEN",
                "SOFTMOBILE_NOTIFICATIONS_WHATSAPP_TOKEN",
            ),
        ),
    ]
    notifications_whatsapp_sender: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_WHATSAPP_SENDER",
                "SOFTMOBILE_NOTIFICATIONS_WHATSAPP_SENDER",
            ),
        ),
    ]
    notifications_whatsapp_timeout: Annotated[
        int,
        Field(
            default=10,
            validation_alias=AliasChoices(
                "NOTIFICATIONS_WHATSAPP_TIMEOUT",
                "SOFTMOBILE_NOTIFICATIONS_WHATSAPP_TIMEOUT",
            ),
        ),
    ]
    risk_alert_email_recipients: Annotated[
        list[str],
        Field(
            default_factory=list,
            validation_alias=AliasChoices(
                "RISK_ALERT_EMAIL_RECIPIENTS",
                "SOFTMOBILE_RISK_ALERT_EMAIL_RECIPIENTS",
            ),
        ),
    ]
    risk_alert_webhook_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "RISK_ALERT_WEBHOOK_URL",
                "SOFTMOBILE_RISK_ALERT_WEBHOOK_URL",
            ),
        ),
    ]
    enable_backup_scheduler: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_BACKUP_SCHEDULER",
                "SOFTMOBILE_ENABLE_BACKUP_SCHEDULER",
            ),
        ),
    ]
    reservations_expiration_interval_seconds: Annotated[
        int,
        Field(
            default=300,
            validation_alias=AliasChoices(
                "RESERVATIONS_EXPIRATION_INTERVAL_SECONDS",
                "SOFTMOBILE_RESERVATIONS_INTERVAL_SECONDS",
            ),
        ),
    ]
    customer_segmentation_interval_seconds: Annotated[
        int,
        Field(
            default=43200,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENTATION_INTERVAL_SECONDS",
                "SOFTMOBILE_CUSTOMER_SEGMENT_INTERVAL",
            ),
        ),
    ]
    customer_segment_window_days: Annotated[
        int,
        Field(
            default=365,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_WINDOW_DAYS",
                "SOFTMOBILE_CUSTOMER_SEGMENT_WINDOW_DAYS",
            ),
        ),
    ]
    customer_segment_ttl_seconds: Annotated[
        int,
        Field(
            default=43200,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_TTL_SECONDS",
                "SOFTMOBILE_CUSTOMER_SEGMENT_TTL",
            ),
        ),
    ]
    customer_segment_high_value_threshold: Annotated[
        Decimal,
        Field(
            default=Decimal("10000"),
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_HIGH_VALUE_THRESHOLD",
                "SOFTMOBILE_CUSTOMER_SEGMENT_HIGH_VALUE",
            ),
        ),
    ]
    customer_segment_medium_value_threshold: Annotated[
        Decimal,
        Field(
            default=Decimal("3000"),
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_MEDIUM_VALUE_THRESHOLD",
                "SOFTMOBILE_CUSTOMER_SEGMENT_MEDIUM_VALUE",
            ),
        ),
    ]
    customer_segment_frequent_orders_threshold: Annotated[
        int,
        Field(
            default=12,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_FREQUENT_ORDERS_THRESHOLD",
                "SOFTMOBILE_CUSTOMER_SEGMENT_FREQUENT_ORDERS",
            ),
        ),
    ]
    customer_segment_regular_orders_threshold: Annotated[
        int,
        Field(
            default=4,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_REGULAR_ORDERS_THRESHOLD",
                "SOFTMOBILE_CUSTOMER_SEGMENT_REGULAR_ORDERS",
            ),
        ),
    ]
    customer_segment_recovery_days: Annotated[
        int,
        Field(
            default=180,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_RECOVERY_DAYS",
                "SOFTMOBILE_CUSTOMER_SEGMENT_RECOVERY_DAYS",
            ),
        ),
    ]
    customer_segment_new_customer_days: Annotated[
        int,
        Field(
            default=45,
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENT_NEW_CUSTOMER_DAYS",
                "SOFTMOBILE_CUSTOMER_SEGMENT_NEW_DAYS",
            ),
        ),
    ]
    customer_segments_mailchimp_labels: Annotated[
        list[str],
        Field(
            default_factory=lambda: ["alto_valor"],
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENTS_MAILCHIMP_LABELS",
                "SOFTMOBILE_CUSTOMER_SEGMENTS_MAILCHIMP",
            ),
        ),
    ]
    customer_segments_sms_labels: Annotated[
        list[str],
        Field(
            default_factory=lambda: ["recuperacion"],
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENTS_SMS_LABELS",
                "SOFTMOBILE_CUSTOMER_SEGMENTS_SMS",
            ),
        ),
    ]
    customer_segments_export_directory: Annotated[
        str,
        Field(
            default="logs/customer_segments",
            validation_alias=AliasChoices(
                "CUSTOMER_SEGMENTS_EXPORT_DIRECTORY",
                "SOFTMOBILE_CUSTOMER_SEGMENTS_EXPORT_DIR",
            ),
        ),
    ]
    mailchimp_api_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "MAILCHIMP_API_URL",
                "SOFTMOBILE_MAILCHIMP_API_URL",
            ),
        ),
    ]
    mailchimp_api_key: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "MAILCHIMP_API_KEY",
                "SOFTMOBILE_MAILCHIMP_API_KEY",
            ),
        ),
    ]
    sms_campaign_api_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "SMS_CAMPAIGN_API_URL",
                "SOFTMOBILE_SMS_CAMPAIGN_API_URL",
            ),
        ),
    ]
    sms_campaign_api_token: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "SMS_CAMPAIGN_API_TOKEN",
                "SOFTMOBILE_SMS_CAMPAIGN_API_TOKEN",
            ),
        ),
    ]
    sms_campaign_sender: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "SMS_CAMPAIGN_SENDER",
                "SOFTMOBILE_SMS_CAMPAIGN_SENDER",
            ),
        ),
    ]
    enable_catalog_pro: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_CATALOG_PRO",
                "SOFTMOBILE_ENABLE_CATALOG_PRO",
            ),
        ),
    ]
    enable_variants: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_VARIANTS",
                "SOFTMOBILE_ENABLE_VARIANTS",
            ),
        ),
    ]
    enable_bundles: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_BUNDLES",
                "SOFTMOBILE_ENABLE_BUNDLES",
            ),
        ),
    ]
    enable_transfers: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_TRANSFERS",
                "SOFTMOBILE_ENABLE_TRANSFERS",
            ),
        ),
    ]
    enable_purchases_sales: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_PURCHASES_SALES",
                "SOFTMOBILE_ENABLE_PURCHASES_SALES",
            ),
        ),
    ]
    purchases_documents_backend: Annotated[
        str,
        Field(
            default="local",
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_BACKEND",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_BACKEND",
            ),
        ),
    ]
    purchases_documents_local_path: Annotated[
        str,
        Field(
            default_factory=lambda: str(
                (Path(__file__).resolve().parents[2] / "backups" / "purchase_orders")
            ),
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_LOCAL_PATH",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_LOCAL_PATH",
            ),
        ),
    ]
    purchases_documents_public_url: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_PUBLIC_URL",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_PUBLIC_URL",
            ),
        ),
    ]
    purchases_documents_s3_bucket: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_BUCKET",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_BUCKET",
            ),
        ),
    ]
    purchases_documents_s3_region: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_REGION",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_REGION",
            ),
        ),
    ]
    purchases_documents_s3_endpoint: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_ENDPOINT",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_ENDPOINT",
            ),
        ),
    ]
    purchases_documents_s3_access_key: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_ACCESS_KEY",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_ACCESS_KEY",
            ),
        ),
    ]
    purchases_documents_s3_secret_key: Annotated[
        str | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_SECRET_KEY",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_SECRET_KEY",
            ),
        ),
    ]
    purchases_documents_s3_prefix: Annotated[
        str,
        Field(
            default="purchase_orders",
            validation_alias=AliasChoices(
                "PURCHASES_DOCUMENTS_S3_PREFIX",
                "SOFTMOBILE_PURCHASES_DOCUMENTS_S3_PREFIX",
            ),
        ),
    ]
    pos_payment_terminals: Annotated[
        dict[str, dict[str, Any]],
        Field(
            default_factory=lambda: {
                "atl-01": {
                    "label": "Terminal Atlántida",
                    "adapter": "banco_atlantida",
                    "currency": "HNL",
                },
                "fic-01": {
                    "label": "Terminal Ficohsa",
                    "adapter": "banco_ficohsa",
                    "currency": "HNL",
                },
            },
            validation_alias=AliasChoices(
                "POS_PAYMENT_TERMINALS",
                "SOFTMOBILE_POS_PAYMENT_TERMINALS",
            ),
        ),
    ]
    pos_tip_suggestions: Annotated[
        list[Decimal],
        Field(
            default_factory=lambda: [
                Decimal("0"),
                Decimal("5"),
                Decimal("10"),
            ],
            validation_alias=AliasChoices(
                "POS_TIP_SUGGESTIONS",
                "SOFTMOBILE_POS_TIP_SUGGESTIONS",
            ),
        ),
    ]
    enable_price_lists: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_PRICE_LISTS",
                "SOFTMOBILE_ENABLE_PRICE_LISTS",
            ),
        ),
    ]
    enable_pos_promotions: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_POS_PROMOTIONS",
                "SOFTMOBILE_ENABLE_POS_PROMOTIONS",
            ),
        ),
    ]
    enable_pos_promotions_volume: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_POS_PROMOTIONS_VOLUME",
                "SOFTMOBILE_ENABLE_POS_PROMOTIONS_VOLUME",
            ),
        ),
    ]
    enable_pos_promotions_combo: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_POS_PROMOTIONS_COMBO",
                "SOFTMOBILE_ENABLE_POS_PROMOTIONS_COMBO",
            ),
        ),
    ]
    enable_pos_promotions_coupons: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_POS_PROMOTIONS_COUPONS",
                "SOFTMOBILE_ENABLE_POS_PROMOTIONS_COUPONS",
            ),
        ),
    ]
    enable_analytics_adv: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_ANALYTICS_ADV",
                "SOFTMOBILE_ENABLE_ANALYTICS_ADV",
            ),
        ),
    ]
    enable_2fa: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_2FA", "SOFTMOBILE_ENABLE_2FA"),
        ),
    ]
    enable_hybrid_prep: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ENABLE_HYBRID_PREP",
                "SOFTMOBILE_ENABLE_HYBRID_PREP",
            ),
        ),
    ]
    enable_wms_bins: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_WMS_BINS",
                "SOFTMOBILE_ENABLE_WMS_BINS",
            ),
        ),
    ]
    enable_price_lists: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "ENABLE_PRICE_LISTS",
                "SOFTMOBILE_ENABLE_PRICE_LISTS",
            ),
        ),
    ]
    inventory_low_stock_threshold: Annotated[
        int,
        Field(
            default=5,
            validation_alias=AliasChoices(
                "INVENTORY_LOW_STOCK_THRESHOLD",
                "SOFTMOBILE_LOW_STOCK_THRESHOLD",
            ),
        ),
    ]
    inventory_adjustment_variance_threshold: Annotated[
        int,
        Field(
            default=3,
            validation_alias=AliasChoices(
                "INVENTORY_ADJUSTMENT_VARIANCE_THRESHOLD",
                "SOFTMOBILE_ADJUSTMENT_VARIANCE_THRESHOLD",
            ),
        ),
    ]
    defective_returns_store_id: Annotated[
        int | None,
        Field(
            default=None,
            validation_alias=AliasChoices(
                "DEFECTIVE_RETURNS_STORE_ID",
                "SOFTMOBILE_DEFECTIVE_RETURNS_STORE_ID",
            ),
        ),
    ]
    default_credit_installments: Annotated[
        int,
        Field(
            default=4,
            validation_alias=AliasChoices(
                "DEFAULT_CREDIT_INSTALLMENTS",
                "SOFTMOBILE_CREDIT_INSTALLMENTS",
            ),
        ),
    ]
    default_credit_frequency_days: Annotated[
        int,
        Field(
            default=15,
            validation_alias=AliasChoices(
                "DEFAULT_CREDIT_FREQUENCY_DAYS",
                "SOFTMOBILE_CREDIT_FREQUENCY_DAYS",
            ),
        ),
    ]
    cost_method: Annotated[
        str,
        Field(
            default="FIFO",
            validation_alias=AliasChoices(
                "COST_METHOD", "SOFTMOBILE_COST_METHOD"),
        ),
    ]  # // [PACK30-31-BACKEND]
    backup_interval_seconds: Annotated[
        int,
        Field(
            default=43200,
            validation_alias=AliasChoices(
                "BACKUP_INTERVAL_SECONDS",
                "SOFTMOBILE_BACKUP_INTERVAL_SECONDS",
            ),
        ),
    ]
    backup_directory: Annotated[
        str,
        Field(
            default="./backups",
            validation_alias=AliasChoices(
                "BACKUP_DIR", "SOFTMOBILE_BACKUP_DIR"),
        ),
    ]
    accounts_receivable_reminders_enabled: Annotated[
        bool,
        Field(
            default=True,
            validation_alias=AliasChoices(
                "ACCOUNTS_RECEIVABLE_REMINDERS_ENABLED",
                "SOFTMOBILE_ACCOUNTS_RECEIVABLE_REMINDERS_ENABLED",
            ),
        ),
    ]
    accounts_receivable_reminder_interval_seconds: Annotated[
        int,
        Field(
            default=21600,
            validation_alias=AliasChoices(
                "ACCOUNTS_RECEIVABLE_REMINDER_INTERVAL_SECONDS",
                "SOFTMOBILE_ACCOUNTS_RECEIVABLE_REMINDER_INTERVAL_SECONDS",
            ),
        ),
    ]
    accounts_receivable_reminder_days_before_due: Annotated[
        int,
        Field(
            default=3,
            validation_alias=AliasChoices(
                "ACCOUNTS_RECEIVABLE_REMINDER_DAYS_BEFORE_DUE",
                "SOFTMOBILE_ACCOUNTS_RECEIVABLE_REMINDER_DAYS",
            ),
        ),
    ]
    update_feed_path: Annotated[
        str,
        Field(
            default="./docs/releases.json",
            validation_alias=AliasChoices(
                "UPDATE_FEED_PATH",
                "SOFTMOBILE_UPDATE_FEED_PATH",
            ),
        ),
    ]
    session_cookie_name: Annotated[
        str,
        Field(
            default="softmobile_session",
            validation_alias=AliasChoices(
                "SESSION_COOKIE_NAME",
                "SOFTMOBILE_SESSION_COOKIE_NAME",
            ),
        ),
    ]
    session_cookie_secure: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "SESSION_COOKIE_SECURE",
                "SOFTMOBILE_SESSION_COOKIE_SECURE",
            ),
        ),
    ]
    session_cookie_samesite: Annotated[
        str,
        Field(
            default="lax",
            validation_alias=AliasChoices(
                "SESSION_COOKIE_SAMESITE",
                "SOFTMOBILE_SESSION_COOKIE_SAMESITE",
            ),
        ),
    ]
    allowed_origins: Annotated[
        list[str],
        Field(
            ...,
            validation_alias=AliasChoices(
                "CORS_ORIGINS", "SOFTMOBILE_ALLOWED_ORIGINS"
            ),
        ),
    ]
    testing_mode: Annotated[
        bool,
        Field(
            default=False,
            validation_alias=AliasChoices(
                "SOFTMOBILE_TEST_MODE", "TESTING_MODE"
            ),
        ),
    ]

    @field_validator("pos_payment_terminals", mode="before")
    @classmethod
    def _parse_pos_terminals(
        cls, value: Any, info: ValidationInfo
    ) -> dict[str, dict[str, Any]]:
        if value is None:
            return {}
        data: Any = value
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return {}
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "POS_PAYMENT_TERMINALS debe ser JSON válido"
                ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                "POS_PAYMENT_TERMINALS debe ser un objeto JSON con terminales",
            )
        normalized: dict[str, dict[str, Any]] = {}
        for key, cfg in data.items():
            if not isinstance(cfg, dict):
                raise ValueError(
                    f"Configuración inválida para el terminal {key!r}",
                )
            normalized[key] = cfg
        return normalized

    @field_validator("pos_tip_suggestions", mode="before")
    @classmethod
    def _parse_tip_suggestions(cls, value: Any) -> list[Decimal]:
        if value is None:
            return []
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return []
            parts = [part.strip() for part in raw.split(",") if part.strip()]
            return [Decimal(part) for part in parts]
        if isinstance(value, (list, tuple)):
            return [Decimal(str(part)) for part in value]
        raise ValueError("POS_TIP_SUGGESTIONS debe ser una lista o CSV de números")

    @field_validator("pos_tip_suggestions")
    @classmethod
    def _validate_tip_suggestions(
        cls, value: list[Decimal]
    ) -> list[Decimal]:
        normalized: list[Decimal] = []
        for amount in value:
            decimal_value = Decimal(str(amount))
            if decimal_value < Decimal("0"):
                raise ValueError("Las propinas sugeridas deben ser no negativas")
            normalized.append(decimal_value.quantize(Decimal("0.01")))
        return normalized

    @field_validator("pos_payment_terminals")
    @classmethod
    def _validate_pos_terminals(
        cls, value: dict[str, dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for key, cfg in value.items():
            if "adapter" not in cfg:
                raise ValueError(
                    f"El terminal {key!r} debe indicar el adaptador bancario",
                )
            normalized[key] = cfg
        return normalized

    @model_validator(mode="after")
    def _ensure_testing_flag(self) -> "Settings":
        if bool(os.getenv("PYTEST_CURRENT_TEST")):
            self.testing_mode = True
        return self

    @field_validator(
        "access_token_expire_minutes",
        "sync_interval_seconds",
        "sync_retry_interval_seconds",
        "sync_max_attempts",
        "backup_interval_seconds",
        "session_cookie_expire_minutes",
        "max_failed_login_attempts",
        "account_lock_minutes",
        "password_reset_token_minutes",
        # // [PACK28-config]
        "refresh_token_expire_days",
    )
    @classmethod
    def _ensure_positive(cls, value: int, info: ValidationInfo) -> int:
        if value <= 0:
            raise ValueError(f"{info.field_name} debe ser mayor que cero")
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: Any) -> list[str]:
        # Soporta lista JSON en cadena (por compatibilidad) o CSV simple
        if isinstance(value, str):
            raw = value.strip()
            if raw.startswith("["):
                try:
                    import json
                    parsed = json.loads(raw)
                    if isinstance(parsed, (list, tuple)):
                        return [str(o).strip() for o in parsed if str(o).strip()]
                except Exception:
                    # Si falla, continuar con CSV
                    pass
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        if isinstance(value, (list, tuple)):
            return [str(origin).strip() for origin in value if str(origin).strip()]
        raise ValueError(
            "allowed_origins debe ser una lista de orígenes válidos")

    @field_validator("session_cookie_samesite", mode="before")
    @classmethod
    def _normalize_samesite(cls, value: Any) -> str:
        if value is None:
            return "lax"
        normalized = str(value).strip().lower()
        if normalized not in {"lax", "strict", "none"}:
            raise ValueError(
                "session_cookie_samesite debe ser lax, strict o none")
        return normalized

    @field_validator(
        "inventory_low_stock_threshold",
        "inventory_adjustment_variance_threshold",
    )
    @classmethod
    def _ensure_non_negative(cls, value: int, info: ValidationInfo) -> int:
        if value < 0:
            raise ValueError(
                f"{info.field_name} debe ser mayor o igual que cero")
        return value

    @field_validator("cost_method", mode="before")
    @classmethod
    def _normalize_cost_method(cls, value: str | None) -> str:
        normalized = (value or "FIFO").strip().upper()
        if normalized not in {"FIFO", "AVG"}:
            return "FIFO"
        return normalized  # // [PACK30-31-BACKEND]

    @field_validator(
        "enable_background_scheduler",
        "enable_backup_scheduler",
        "enable_catalog_pro",
        "enable_transfers",
        "enable_purchases_sales",
        "enable_price_lists",
        "enable_pos_promotions",
        "enable_pos_promotions_volume",
        "enable_pos_promotions_combo",
        "enable_pos_promotions_coupons",
        "enable_analytics_adv",
        "enable_2fa",
        "enable_hybrid_prep",
        "enable_wms_bins",
        "session_cookie_secure",
    )
    @classmethod
    def _coerce_bool(cls, value: bool | str | int | None) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if value is None:
            return False
        return _is_truthy(str(value))

    @field_validator("notifications_email_use_tls", mode="before")
    @classmethod
    def _coerce_notifications_tls(cls, value: bool | str | int | None) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if value is None:
            return True
        return _is_truthy(str(value))

    @field_validator("notifications_whatsapp_timeout", mode="before")
    @classmethod
    def _normalize_whatsapp_timeout(cls, value: int | str | None) -> int:
        if isinstance(value, int):
            return value
        if value is None or (isinstance(value, str) and not value.strip()):
            return 10
        try:
            return int(str(value).strip())
        except ValueError as exc:  # pragma: no cover - validación defensiva
            raise ValueError("notifications_whatsapp_timeout_invalid") from exc

    @field_validator("purchases_documents_backend", mode="before")
    @classmethod
    def _normalize_purchase_backend(cls, value: str | None) -> str:
        if value is None:
            return "local"
        normalized = str(value).strip().lower()
        if normalized not in {"local", "s3"}:
            raise ValueError("purchases_documents_backend_invalid")
        return normalized

    @field_validator("purchases_documents_local_path", mode="before")
    @classmethod
    def _normalize_purchase_local_path(cls, value: str | Path | None) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            base = Path(__file__).resolve().parents[2] / "backups" / "purchase_orders"
            return str(base)
        return str(Path(value).expanduser())

    @field_validator("config_sync_directory", mode="before")
    @classmethod
    def _normalize_config_sync_directory(
        cls, value: str | Path | None
    ) -> str:
        if value is None or (isinstance(value, str) and not value.strip()):
            default_path = (
                Path(__file__).resolve().parents[2] / "ops" / "config_sync"
            )
            return str(default_path)
        return str(Path(value).expanduser())

    @field_validator("config_sync_enabled", mode="before")
    @classmethod
    def _normalize_config_sync_enabled(cls, value: bool | str | None) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        if value is None or (isinstance(value, str) and not value.strip()):
            return True
        return _is_truthy(str(value))

    @property
    def purchases_documents_directory(self) -> Path:
        return Path(self.purchases_documents_local_path).expanduser()

    @property
    def config_sync_path(self) -> Path:
        return Path(self.config_sync_directory).expanduser()

    @model_validator(mode="after")
    def _validate_required(self) -> "Settings":
        missing: list[str] = []
        if not self.database_url:
            missing.append("DATABASE_URL")
        if not self.secret_key:
            missing.append("JWT_SECRET_KEY")
        if not self.allowed_origins:
            missing.append("CORS_ORIGINS")
        if missing:
            raise ValueError(
                "Faltan variables de entorno obligatorias: " +
                ", ".join(missing)
            )
        return self


try:
    settings = Settings()
except ValidationError as exc:  # pragma: no cover - validado en pruebas manuales
    missing = [
        str(error.get("loc", ("",))[0])
        for error in exc.errors()
        if error.get("type") == "missing"
    ]
    details = ", ".join(sorted(set(missing))) or "valores requeridos"
    raise RuntimeError(
        "Faltan variables de entorno obligatorias para iniciar el backend: "
        f"{details}."
    ) from exc
