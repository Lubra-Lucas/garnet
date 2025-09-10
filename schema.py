# schema.py
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, validator

# User schemas
class UserCreate(BaseModel):
    username: str
    name: str
    role: str = "viewer"
    password: str

class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    role: str
    is_active: bool
    created_at: datetime

# Supplier schemas
class SupplierCreate(BaseModel):
    name: str
    cnpj: Optional[str] = None
    phone: Optional[str] = None
    telefone_residencial: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    avg_leadtime_days: Optional[int] = None
    certifications: Optional[str] = None
    certification_file_path: Optional[str] = None
    notes: Optional[str] = None

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    cnpj: Optional[str] = None
    phone: Optional[str] = None
    telefone_residencial: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    avg_leadtime_days: Optional[int] = None
    certifications: Optional[str] = None
    certification_file_path: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None

# Raw Material schemas
class RawMaterialCreate(BaseModel):
    code: str
    name_usual: str
    name_chemical: Optional[str] = None
    supplier_id: Optional[int] = None
    base_unit: str
    base_price: float = 0.0
    density: Optional[float] = None
    conv_factor: Optional[float] = None
    shelf_life_days: Optional[int] = None
    location: Optional[str] = None

class RawMaterialUpdate(BaseModel):
    name_usual: Optional[str] = None
    name_chemical: Optional[str] = None
    supplier_id: Optional[int] = None
    base_unit: Optional[str] = None
    base_price: Optional[float] = None
    density: Optional[float] = None
    conv_factor: Optional[float] = None
    shelf_life_days: Optional[int] = None
    location: Optional[str] = None
    status: Optional[str] = None

# Product schemas
class ProductCreate(BaseModel):
    code: str
    name: str
    client: Optional[str] = None
    category: Optional[str] = None
    unit_weight: float = 0.0
    unit_uom: str = "G"
    std_batch_weight: float = 1500.0

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    client: Optional[str] = None
    category: Optional[str] = None
    unit_weight: Optional[float] = None
    unit_uom: Optional[str] = None
    std_batch_weight: Optional[float] = None
    status: Optional[str] = None

# Stock schemas
class StockLotCreate(BaseModel):
    item_type: str
    item_id: int
    lot_code: str
    qty: float
    uom: str
    expiry: Optional[date] = None
    avg_cost: Optional[float] = None
    location: Optional[str] = None

class StockLotUpdate(BaseModel):
    qty: Optional[float] = None
    status: Optional[str] = None
    location: Optional[str] = None

# Production Order schemas
class ProductionOrderCreate(BaseModel):
    code: str
    product_id: int
    qty_to_produce: float
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    workcenter: Optional[str] = None

class ProductionOrderUpdate(BaseModel):
    qty_to_produce: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    workcenter: Optional[str] = None
    status: Optional[str] = None

# Purchase Order schemas
class PurchaseOrderCreate(BaseModel):
    code: str
    supplier_id: int
    payment_terms: Optional[str] = None

class PurchaseItemCreate(BaseModel):
    raw_material_id: int
    qty: float
    uom: str
    price: float
    due_date: Optional[date] = None

# Formulation schemas
class FormulationCreate(BaseModel):
    product_id: int
    version: str = "v1"

class FormulaItemCreate(BaseModel):
    raw_material_id: int
    qty: float
    uom: str
    percent: Optional[float] = None

# Payable schemas
class PayableCreate(BaseModel):
    supplier_id: Optional[int] = None
    doc_ref: str
    expense_type: Optional[str] = None
    empresa: Optional[str] = None
    value: float
    due_date: date
    status: str = "Pendente"
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None
    is_installment: bool = False
    installment_number: Optional[int] = None
    total_installments: Optional[int] = None
    parent_payable_id: Optional[int] = None

class PayableUpdate(BaseModel):
    supplier_id: Optional[int] = None
    doc_ref: Optional[str] = None
    expense_type: Optional[str] = None
    empresa: Optional[str] = None
    value: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None

# Receivable schemas
class ReceivableCreate(BaseModel):
    customer_name: Optional[str] = None
    doc_ref: str
    revenue_type: Optional[str] = None
    empresa: Optional[str] = None
    value: float
    due_date: date
    status: str = "Pendente"
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None
    is_installment: bool = False
    installment_number: Optional[int] = None
    total_installments: Optional[int] = None
    parent_receivable_id: Optional[int] = None

class ReceivableUpdate(BaseModel):
    customer_name: Optional[str] = None
    doc_ref: Optional[str] = None
    revenue_type: Optional[str] = None
    value: Optional[float] = None
    due_date: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None

# Quote Request schemas
class QuoteRequestCreate(BaseModel):
    code: str
    supplier_id: int
    notes: Optional[str] = None

class QuoteRequestUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None

class QuoteItemCreate(BaseModel):
    item_type: str
    item_name: str
    chemical_name: Optional[str] = None
    commercial_name: Optional[str] = None
    min_quantity: float
    unit_price: float
    total_price_with_tax: float
    validity_days: Optional[int] = None
    lead_time_days: Optional[int] = None
    uom: str = "KG"