"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations

from .users import (
    User, Role, Permission, UserTOTPSecret, PasswordResetToken, ActiveSession,
    UserRole, JWTBlacklist
)
from .stores import (
    Store, Warehouse, WMSBin, DeviceBinAssignment
)
from .products import (
    Device, ProductVariant, ProductBundle, ProductBundleItem, DeviceIdentifier,
    CommercialState
)
from .inventory import (
    InventoryMovement, InventoryReservation, StockMove, CostLedgerEntry,
    ImportValidation, InventoryImportTemp, MovementType, StockMoveType,
    CostingMethod, InventoryState
)
from .sales import (
    Sale, SaleItem, POSDocumentType, PaymentMethod, CashSession, CashEntry,
    CashSessionStatus, CashEntryType, ReturnDisposition, ReturnReasonCategory,
    RMAStatus, WarrantyStatus, WarrantyClaimType, WarrantyClaimStatus,
    WarrantyAssignment, WarrantyClaim, RMARequest, PriceList, PriceListItem,
    RETURN_DISPOSITION_ENUM, RETURN_REASON_CATEGORY_ENUM, RMA_STATUS_ENUM,
    WARRANTY_STATUS_ENUM, WARRANTY_CLAIM_STATUS_ENUM, WARRANTY_CLAIM_TYPE_ENUM,
    DTEStatus, DTEDispatchStatus, POSConfig, SaleReturn
)
from .customers import (
    Customer, LoyaltyAccount, StoreCredit, CustomerSegmentSnapshot,
    CustomerPrivacyRequest, CustomerLedgerEntry, CustomerType, CustomerStatus,
    LoyaltyTransactionType, LOYALTY_TRANSACTION_TYPE_ENUM, CustomerLedgerEntryType,
    PrivacyRequestStatus, PrivacyRequestType, StoreCreditStatus,
    generate_customer_tax_id_placeholder
)
from .transfers import (
    TransferOrder, TransferOrderItem, TransferStatus
)
from .purchases import (
    Supplier, SupplierBatch, SupplierLedgerEntry, PurchaseOrder,
    PurchaseOrderItem, PurchaseReturn, PurchaseOrderDocument, PurchaseStatus,
    PurchaseOrderStatusEvent, Proveedor, Compra, DetalleCompra
)
from .repairs import (
    RepairOrder, RepairOrderPart, RepairStatus, RepairPartSource
)
from .audit import (
    AuditLog, AuditAlertAcknowledgement, SystemLog, SystemError, SystemLogLevel,
    FeedbackCategory, FeedbackPriority, FeedbackStatus, SupportFeedback, AuditUI
)
from .sync import (
    SyncSession, SyncOutbox, SyncMode, SyncStatus, SyncOutboxStatus,
    SyncOutboxPriority, SyncQueueStatus
)
from .operations import (
    RecurringOrder, RecurringOrderType
)
from .config import (
    ConfigRate, ConfigXmlTemplate, ConfigParameter, BackupJob, BackupMode,
    BackupComponent
)

__all__ = [
    "User", "Role", "Permission", "UserTOTPSecret", "PasswordResetToken",
    "ActiveSession", "UserRole",
    "Store", "Warehouse", "WMSBin", "DeviceBinAssignment", "PriceList",
    "PriceListItem",
    "Device", "ProductVariant", "ProductBundle", "ProductBundleItem",
    "DeviceIdentifier", "CommercialState",
    "InventoryMovement", "InventoryReservation", "StockMove", "CostLedgerEntry",
    "ImportValidation", "InventoryImportTemp", "MovementType", "StockMoveType",
    "CostingMethod", "InventoryState",
    "Sale", "SaleItem", "POSDocumentType", "PaymentMethod", "CashSession",
    "CashEntry", "CashSessionStatus", "CashEntryType", "ReturnDisposition",
    "ReturnReasonCategory", "RMAStatus", "WarrantyStatus", "WarrantyClaimType",
    "WarrantyClaimStatus", "WarrantyAssignment", "WarrantyClaim", "RMARequest",
    "RETURN_DISPOSITION_ENUM", "RETURN_REASON_CATEGORY_ENUM", "RMA_STATUS_ENUM",
    "WARRANTY_STATUS_ENUM", "WARRANTY_CLAIM_STATUS_ENUM",
    "WARRANTY_CLAIM_TYPE_ENUM", "DTEStatus", "DTEDispatchStatus",
    "Customer", "LoyaltyAccount", "StoreCredit", "CustomerSegmentSnapshot",
    "CustomerPrivacyRequest", "CustomerLedgerEntry", "CustomerType",
    "CustomerStatus", "LoyaltyTransactionType", "LOYALTY_TRANSACTION_TYPE_ENUM",
    "CustomerLedgerEntryType", "PrivacyRequestStatus", "PrivacyRequestType",
    "StoreCreditStatus",
    "TransferOrder", "TransferOrderItem", "TransferStatus",
    "Supplier", "SupplierBatch", "SupplierLedgerEntry", "PurchaseOrder",
    "PurchaseOrderItem", "PurchaseReturn", "PurchaseOrderDocument",
    "PurchaseStatus", "PurchaseOrderStatusEvent", "Proveedor", "Compra",
    "DetalleCompra",
    "RepairOrder", "RepairOrderPart", "RepairStatus", "RepairPartSource",
    "AuditLog", "AuditAlertAcknowledgement", "SystemLog", "SystemError",
    "SystemLogLevel", "FeedbackCategory", "FeedbackPriority", "FeedbackStatus",
    "SupportFeedback", "AuditUI",
    "SyncSession", "SyncOutbox", "SyncMode", "SyncStatus", "SyncOutboxStatus",
    "SyncOutboxPriority", "SyncQueueStatus",
    "RecurringOrder", "RecurringOrderType",
    "ConfigRate", "ConfigXmlTemplate", "ConfigParameter", "BackupJob",
    "BackupMode", "BackupComponent"
]
