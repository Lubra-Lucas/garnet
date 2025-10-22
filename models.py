# models.py
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
import pytz

# Function to get current datetime in São Paulo timezone
def get_current_datetime():
    return datetime.now(pytz.timezone("America/Sao_Paulo"))

class User(SQLModel, table=True):
    """User model for authentication and authorization"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    name: str
    role: str = Field(default="viewer")  # viewer, operator, manager
    password_hash: str
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)
    is_active: bool = Field(default=True)

class Supplier(SQLModel, table=True):
    """Supplier/Vendor model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    cnpj: Optional[str] = Field(default=None, index=True)
    phone: Optional[str] = None
    email: Optional[str] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    payment_terms: Optional[str] = None
    avg_leadtime_days: Optional[int] = None
    certifications: Optional[str] = None
    certification_file_path: Optional[str] = None  # Path to uploaded certification PDF file
    notes: Optional[str] = None
    status: str = Field(default="ativo")
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class RawMaterial(SQLModel, table=True):
    """Raw Material model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name_usual: str
    name_chemical: Optional[str] = None
    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id")
    base_unit: str  # KG, G, L, ML, UN
    base_price: float = Field(default=0.0)  # preço por unidade base
    density: Optional[float] = None
    conv_factor: Optional[float] = None  # ex.: KG↔G
    shelf_life_days: Optional[int] = None
    location: Optional[str] = None
    certification_file_path: Optional[str] = None  # Path to uploaded certification PDF files (JSON list)
    status: str = Field(default="ativo")
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class Product(SQLModel, table=True):
    """Finished Product model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    name: str
    client: Optional[str] = None
    category: Optional[str] = None
    unit_weight: float = Field(default=0.0)  # g ou ml
    unit_uom: str = Field(default="G")  # G, ML, UN
    std_batch_weight: float = Field(default=1500.0)  # gramas (1,5 kg)
    status: str = Field(default="ativo")
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class Formulation(SQLModel, table=True):
    """Product formulation/recipe model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id")
    version: str = Field(default="v1")
    state: str = Field(default="rascunho")  # rascunho/aprovada/obsoleta
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None

class FormulaItem(SQLModel, table=True):
    """Individual items within a formulation"""
    id: Optional[int] = Field(default=None, primary_key=True)
    formulation_id: int = Field(foreign_key="formulation.id")
    raw_material_id: int = Field(foreign_key="rawmaterial.id")
    qty: float  # quantidade por lote padrão
    uom: str
    percent: Optional[float] = None

class StockLot(SQLModel, table=True):
    """Stock lot tracking for both raw materials and finished products"""
    id: Optional[int] = Field(default=None, primary_key=True)
    item_type: str  # MP (Raw Material) or PA (Finished Product)
    item_id: int  # ID of RawMaterial or Product
    lot_code: str = Field(index=True)
    qty: float
    uom: str
    expiry: Optional[date] = None
    status: str = Field(default="Aprovado")  # Aprovado, Rejeitado, Quarentena
    avg_cost: Optional[float] = None
    location: Optional[str] = None
    received_date: Optional[date] = Field(default_factory=date.today)
    certification_file_path: Optional[str] = None  # Path to uploaded certification PDF files (JSON list)
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class ProductionOrder(SQLModel, table=True):
    """Production order model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    product_id: int = Field(foreign_key="product.id")
    qty_to_produce: float
    planned_lot: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    workcenter: Optional[str] = None
    status: str = Field(default="Planejada")  # Planejada, Em Produção, Concluída, Cancelada
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)
    created_by: Optional[str] = None

class PurchaseOrder(SQLModel, table=True):
    """Purchase order header"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    supplier_id: int = Field(foreign_key="supplier.id")
    order_date: date = Field(default_factory=date.today)
    status: str = Field(default="Aberto")  # Aberto, Enviado, Recebido, Cancelado
    payment_terms: Optional[str] = None
    total_value: float = Field(default=0.0)
    notes: Optional[str] = None  # Campo para armazenar tipo de pedido (Pedido de Compra ou Pedido de Amostra) e outras observações
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class PurchaseItem(SQLModel, table=True):
    """Purchase order line items"""
    id: Optional[int] = Field(default=None, primary_key=True)
    po_id: int = Field(foreign_key="purchaseorder.id")
    raw_material_id: int = Field(foreign_key="rawmaterial.id")
    qty: float
    uom: str
    price: float
    due_date: Optional[date] = None
    received_qty: float = Field(default=0.0)

class Payable(SQLModel, table=True):
    """Accounts payable model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    supplier_id: Optional[int] = Field(default=None, foreign_key="supplier.id")
    doc_ref: str  # Document reference (invoice number, contract, etc.)
    expense_type: Optional[str] = None  # Type of expense (materials, services, etc.)
    empresa: Optional[str] = None  # Company making the payment
    value: float
    due_date: date
    status: str = Field(default="Pendente")  # Pendente, Pago, Vencido
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None  # Path to uploaded XML file
    is_installment: bool = Field(default=False)  # If this is an installment payment
    installment_number: Optional[int] = None  # Current installment number (1, 2, 3...)
    total_installments: Optional[int] = None  # Total number of installments
    parent_payable_id: Optional[int] = Field(default=None, foreign_key="payable.id")  # Reference to parent if installment
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class Receivable(SQLModel, table=True):
    """Accounts receivable model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    customer_name: Optional[str] = None  # Customer name since we don't have a customer table yet
    doc_ref: str  # Document reference (invoice number, contract, etc.)
    revenue_type: Optional[str] = None  # Type of revenue (product sales, services, etc.)
    value: float
    due_date: date
    status: str = Field(default="Pendente")  # Pendente, Recebido, Vencido
    notes: Optional[str] = None
    xml_file_path: Optional[str] = None  # Path to uploaded XML file
    is_installment: bool = Field(default=False)  # If this is an installment payment
    installment_number: Optional[int] = None  # Current installment number (1, 2, 3...)
    total_installments: Optional[int] = None  # Total number of installments
    parent_receivable_id: Optional[int] = Field(default=None, foreign_key="receivable.id")  # Reference to parent if installment
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)

class QuoteRequest(SQLModel, table=True):
    """Quote request header model"""
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    request_number: Optional[str] = Field(default=None, index=True)  # Número da solicitação
    supplier_id: int = Field(foreign_key="supplier.id")
    request_date: date = Field(default_factory=date.today)
    status: str = Field(default="Pendente")  # Pendente, Aprovado, Arquivado
    notes: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)
    created_by: Optional[str] = None
    
    # Relationship
    items: list["QuoteItem"] = Relationship(back_populates="quote_request")

class QuoteItem(SQLModel, table=True):
    """Quote request line items"""
    id: Optional[int] = Field(default=None, primary_key=True)
    quote_request_id: int = Field(foreign_key="quoterequest.id")
    item_type: str  # MP (Raw Material) or PA (Finished Product)
    item_name: str  # Product name
    chemical_name: Optional[str] = None  # For raw materials
    commercial_name: Optional[str] = None  # For raw materials
    min_quantity: float
    unit_price: float
    total_price_with_tax: float
    validity_days: Optional[int] = None
    lead_time_days: Optional[int] = None
    uom: str = Field(default="KG")
    
    # Relationship
    quote_request: Optional["QuoteRequest"] = Relationship(back_populates="items")

class StockMovement(SQLModel, table=True):
    """Stock movement tracking for entries and withdrawals"""
    id: Optional[int] = Field(default=None, primary_key=True)
    movement_type: str  # Entrada, Saída
    item_type: str  # MP (Raw Material) or PA (Finished Product)
    item_id: int  # ID of RawMaterial or Product
    item_code: str  # Code of the item for quick reference
    item_name: str  # Name of the item for quick reference
    lot_code: str
    qty: float
    uom: str
    reason: str  # Entrada Manual, Baixa Manual, Produção, Ajuste de Inventário, etc.
    notes: Optional[str] = None
    user: Optional[str] = None  # User who made the movement
    movement_date: datetime = Field(default_factory=lambda: get_current_datetime())
    created_at: Optional[datetime] = Field(default_factory=lambda: get_current_datetime())

class QualityTest(SQLModel, table=True):
    """Quality control test results"""
    id: Optional[int] = Field(default=None, primary_key=True)
    lot_id: int = Field(foreign_key="stocklot.id")
    test_type: str  # Físico-Químico, Microbiológico, Sensorial
    parameter: str
    result: str
    specification: Optional[str] = None
    status: str = Field(default="Conforme")  # Conforme, Não Conforme
    tested_by: Optional[str] = None
    test_date: date = Field(default_factory=date.today)
    created_at: Optional[datetime] = Field(default_factory=get_current_datetime)