"""Modelos ORM del dominio de Softmobile Central."""
from __future__ import annotations
from .cloud_agent import (
    CloudAgentTask, CloudAgentTaskStatus, CloudAgentTaskType
)
from .config import (
    ConfigRate, ConfigXmlTemplate, ConfigParameter, BackupJob, BackupMode,
    BackupComponent
)
from .operations import (
    RecurringOrder, RecurringOrderType
)
from .sync import (
    SyncSession, SyncOutbox, SyncMode, SyncStatus, SyncOutboxStatus,
    SyncOutboxPriority, SyncQueueStatus, SyncQueue, SyncAttempt
)
from .audit import (
    AuditLog, AuditAlertAcknowledgement, SystemLog, SystemError, SystemLogLevel,
    FeedbackCategory, FeedbackPriority, FeedbackStatus, SupportFeedback, AuditUI
)

from .users import (
    User, Role, Permission, UserTOTPSecret, PasswordResetToken, ActiveSession,
    UserRole, JWTBlacklist, StoreMembership
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
    WarrantyAssignment, WarrantyClaim, RMARequest, RMAEvent, PriceList, PriceListItem,
    RETURN_DISPOSITION_ENUM, RETURN_REASON_CATEGORY_ENUM, RMA_STATUS_ENUM,
    WARRANTY_STATUS_ENUM, WARRANTY_CLAIM_STATUS_ENUM, WARRANTY_CLAIM_TYPE_ENUM,
    DTEStatus, DTEDispatchStatus, POSConfig, SaleReturn, CashRegisterSession, DTEDocument,
    CashRegisterEntry, DTEAuthorization, DTEDispatchQueue, POSDraftSale, FiscalDocument
)
from .customers import (
    Customer, LoyaltyAccount, StoreCredit, CustomerSegmentSnapshot,
    CustomerPrivacyRequest, CustomerLedgerEntry, CustomerType, CustomerStatus,
    LoyaltyTransactionType, LOYALTY_TRANSACTION_TYPE_ENUM, CustomerLedgerEntryType,
    PrivacyRequestStatus, PrivacyRequestType, StoreCreditStatus,
    generate_customer_tax_id_placeholder, LoyaltyTransaction, StoreCreditRedemption
)
from .transfers import (
    TransferOrder, TransferOrderItem, TransferStatus
)
from .purchases import (
    Supplier, SupplierBatch, SupplierLedgerEntry, SupplierLedgerEntryType, PurchaseOrder,
    PurchaseOrderItem, PurchaseReturn, PurchaseOrderDocument, PurchaseStatus,
    PurchaseOrderStatusEvent, Proveedor, Compra, DetalleCompra
)
from .repairs import (
    RepairOrder, RepairOrderPart, RepairStatus, RepairPartSource
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


__all__ = [
    "Base",
    "User", "Role", "Permission", "UserTOTPSecret", "PasswordResetToken",
    "ActiveSession", "UserRole", "StoreMembership",
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
    "WarrantyClaimStatus", "WarrantyAssignment", "WarrantyClaim", "RMARequest", "RMAEvent",
    "RETURN_DISPOSITION_ENUM", "RETURN_REASON_CATEGORY_ENUM", "RMA_STATUS_ENUM",
    "WARRANTY_STATUS_ENUM", "WARRANTY_CLAIM_STATUS_ENUM",
    "WARRANTY_CLAIM_TYPE_ENUM", "DTEStatus", "DTEDispatchStatus", "CashRegisterSession", "DTEDocument",
    "CashRegisterEntry", "DTEAuthorization", "DTEDispatchQueue",
    "Customer", "LoyaltyAccount", "StoreCredit", "CustomerSegmentSnapshot",
    "CustomerPrivacyRequest", "CustomerLedgerEntry", "CustomerType",
    "CustomerStatus", "LoyaltyTransactionType", "LOYALTY_TRANSACTION_TYPE_ENUM",
    "CustomerLedgerEntryType", "PrivacyRequestStatus", "PrivacyRequestType",
    "StoreCreditStatus", "LoyaltyTransaction", "StoreCreditRedemption",
    "TransferOrder", "TransferOrderItem", "TransferStatus",
    "Supplier", "SupplierBatch", "SupplierLedgerEntry", "SupplierLedgerEntryType", "PurchaseOrder",
    "PurchaseOrderItem", "PurchaseReturn", "PurchaseOrderDocument",
    "PurchaseStatus", "PurchaseOrderStatusEvent", "Proveedor", "Compra",
    "DetalleCompra",
    "RepairOrder", "RepairOrderPart", "RepairStatus", "RepairPartSource",
    "AuditLog", "AuditAlertAcknowledgement", "SystemLog", "SystemError",
    "SystemLogLevel", "FeedbackCategory", "FeedbackPriority", "FeedbackStatus",
    "SupportFeedback", "AuditUI",
    "SyncSession", "SyncOutbox", "SyncMode", "SyncStatus", "SyncOutboxStatus",
    "SyncOutboxPriority", "SyncQueueStatus", "SyncQueue", "SyncAttempt",
    "RecurringOrder", "RecurringOrderType",
    "ConfigRate", "ConfigXmlTemplate", "ConfigParameter", "BackupJob",
    "BackupMode", "BackupComponent",
    "CloudAgentTask", "CloudAgentTaskStatus", "CloudAgentTaskType",
    "POSDraftSale", "FiscalDocument",
]
