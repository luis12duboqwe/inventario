"""Utilidades para enmascaramiento de datos sensibles y privacidad."""
from __future__ import annotations

import re
from collections.abc import Sequence

from .. import models


def mask_email(value: str) -> str:
    """Enmascara un email mostrando solo el primer y último carácter del local.
    
    Args:
        value: Email a enmascarar
        
    Returns:
        Email enmascarado (ej: "j***n@example.com")
    """
    email = (value or "").strip()
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    local = local.strip()
    domain = domain.strip() or "anon.invalid"
    if not local:
        return f"***@{domain}"
    if len(local) == 1:
        masked_local = "*"
    elif len(local) == 2:
        masked_local = f"{local[0]}*"
    else:
        masked_local = f"{local[0]}{'*' * (len(local) - 2)}{local[-1]}"
    return f"{masked_local}@{domain}"


def mask_phone(value: str) -> str:
    """Enmascara un teléfono mostrando solo los últimos 4 dígitos.
    
    Args:
        value: Teléfono a enmascarar
        
    Returns:
        Teléfono enmascarado (ej: "****5678")
    """
    digits = re.sub(r"[^0-9]", "", value or "")
    if not digits:
        return "***"
    if len(digits) <= 4:
        visible = digits[-1:] if digits else ""
        return f"{'*' * max(0, len(digits) - 1)}{visible}"
    return f"{'*' * (len(digits) - 4)}{digits[-4:]}"


def mask_person_name(value: str) -> str:
    """Enmascara un nombre de persona mostrando solo la primera letra de cada palabra.
    
    Args:
        value: Nombre a enmascarar
        
    Returns:
        Nombre enmascarado (ej: "J*** D***")
    """
    text = (value or "").strip()
    if not text:
        return text
    parts = text.split()
    masked_parts = []
    for part in parts:
        if len(part) <= 2:
            masked_parts.append(part[0] + "*")
        else:
            masked_parts.append(part[0] + "*" * (len(part) - 1))
    return " ".join(masked_parts)


def mask_generic_text(value: str) -> str:
    """Enmascara texto genérico mostrando los primeros 2 y últimos 2 caracteres.
    
    Args:
        value: Texto a enmascarar
        
    Returns:
        Texto enmascarado (ej: "ab***yz")
    """
    text = (value or "").strip()
    if not text:
        return text
    if len(text) <= 4:
        return "*" * len(text)
    return f"{text[:2]}***{text[-2:]}"


def apply_customer_anonymization(
    customer: models.Customer, fields: Sequence[str]
) -> list[str]:
    """Aplica enmascaramiento a campos específicos de un cliente.
    
    Args:
        customer: Cliente a anonimizar (se modifica in-place)
        fields: Lista de campos a enmascarar
        
    Returns:
        Lista de campos que fueron enmascarados
        
    Notas:
        Modifica el objeto customer directamente.
        Campos soportados: name, contact_name, email, phone, address, notes, tax_id, history
    """
    normalized: list[str] = []
    for raw in fields or []:
        text = str(raw or "").strip().lower()
        if text and text not in normalized:
            normalized.append(text)

    masked: list[str] = []
    for field in normalized:
        if field == "name" and customer.name:
            customer.name = mask_person_name(customer.name)
            masked.append("name")
        elif field == "contact_name" and customer.contact_name:
            customer.contact_name = mask_person_name(customer.contact_name)
            masked.append("contact_name")
        elif field == "email" and customer.email:
            customer.email = mask_email(customer.email)
            masked.append("email")
        elif field == "phone" and customer.phone:
            customer.phone = mask_phone(customer.phone)
            masked.append("phone")
        elif field == "address" and customer.address:
            customer.address = mask_generic_text(customer.address)
            masked.append("address")
        elif field == "notes" and customer.notes:
            customer.notes = mask_generic_text(customer.notes)
            masked.append("notes")
        elif field == "tax_id" and customer.tax_id:
            customer.tax_id = mask_generic_text(customer.tax_id)
            masked.append("tax_id")

    if "history" in normalized and customer.history:
        history_entries = list(customer.history or [])
        customer.history = [
            {
                "timestamp": entry.get("timestamp"),
                "note": "***",
            }
            for entry in history_entries
        ]
        masked.append("history")

    return masked
