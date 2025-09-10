# services/business.py
from sqlmodel import Session, select
from models import RawMaterial, Product, Formulation, FormulaItem, StockLot
from typing import List, Tuple, Optional
from datetime import date

def material_cost_unit(rm: RawMaterial, qty: float, uom: str) -> float:
    """Calculate cost of raw material for given quantity and unit"""
    # Normalize unit strings for comparison
    base_unit = rm.base_unit.upper().strip()
    input_uom = uom.upper().strip()

    # Convert input quantity to base unit for cost calculation
    qty_in_base_unit = qty

    # Convert weight units
    if base_unit == "KG" and input_uom in ["G", "GRAMAS", "GRAMA"]:
        qty_in_base_unit = qty / 1000  # Convert grams to kg
    elif base_unit in ["G", "GRAMAS", "GRAMA"] and input_uom == "KG":
        qty_in_base_unit = qty * 1000  # Convert kg to grams

    # Convert volume units
    elif base_unit == "L" and input_uom in ["ML", "MILILITRO", "MILILITROS"]:
        qty_in_base_unit = qty / 1000  # Convert ml to liters
    elif base_unit in ["ML", "MILILITRO", "MILILITROS"] and input_uom == "L":
        qty_in_base_unit = qty * 1000  # Convert liters to ml

    # Handle cross-unit conversions using density (mass <-> volume)
    elif rm.density:
        if base_unit == "KG" and input_uom in ["L", "ML", "LITRO", "LITROS", "MILILITRO", "MILILITROS"]:
            # Convert volume to mass: base unit is KG, input is volume
            volume_in_liters = qty if input_uom in ["L", "LITRO", "LITROS"] else qty / 1000
            qty_in_base_unit = volume_in_liters * rm.density  # kg

        elif base_unit in ["G", "GRAMAS", "GRAMA"] and input_uom in ["L", "ML", "LITRO", "LITROS", "MILILITRO", "MILILITROS"]:
            # Convert volume to mass: base unit is G, input is volume
            volume_in_liters = qty if input_uom in ["L", "LITRO", "LITROS"] else qty / 1000
            qty_in_base_unit = volume_in_liters * rm.density * 1000  # grams

        elif base_unit == "L" and input_uom in ["KG", "G", "GRAMAS", "GRAMA"]:
            # Convert mass to volume: base unit is L, input is mass
            mass_in_kg = qty if input_uom == "KG" else qty / 1000
            qty_in_base_unit = mass_in_kg / rm.density  # liters

        elif base_unit in ["ML", "MILILITRO", "MILILITROS"] and input_uom in ["KG", "G", "GRAMAS", "GRAMA"]:
            # Convert mass to volume: base unit is ML, input is mass
            mass_in_kg = qty if input_uom == "KG" else qty / 1000
            qty_in_base_unit = (mass_in_kg / rm.density) * 1000  # ml

    # Calculate proportional cost based on base price per base unit
    final_cost = rm.base_price * qty_in_base_unit

    return final_cost

def formulation_cost(session: Session, formulation_id: int, batch_size: Optional[float] = None) -> Tuple[float, float]:
    """Calculate total cost of formulation and cost per unit"""
    items = session.exec(select(FormulaItem).where(FormulaItem.formulation_id == formulation_id)).all()
    total_cost = 0.0

    for item in items:
        rm = session.get(RawMaterial, item.raw_material_id)
        if rm:
            total_cost += material_cost_unit(rm, item.qty, item.uom)

    # Get product info for unit calculations
    formulation = session.get(Formulation, formulation_id)
    if formulation:
        product = session.get(Product, formulation.product_id)
        if product and batch_size:
            units_per_batch = batch_size / product.unit_weight if product.unit_weight > 0 else 1
            unit_cost = total_cost / units_per_batch if units_per_batch > 0 else 0.0
        else:
            unit_cost = total_cost / product.std_batch_weight if product and product.std_batch_weight > 0 else 0.0
    else:
        unit_cost = 0.0

    return total_cost, unit_cost

def fefo_pick(lots: List[StockLot]) -> List[StockLot]:
    """Sort lots by FEFO (First Expired, First Out) logic"""
    return sorted(lots, key=lambda x: (x.expiry or date.max, x.id))

def calculate_stock_value(session: Session, item_type: str = None):
    """Calculate total stock value for active items only"""
    from sqlmodel import text

    if item_type == "MP":
        # Only calculate for active raw materials
        query = text("""
        SELECT sl.qty, sl.avg_cost
        FROM stocklot sl
        INNER JOIN rawmaterial rm ON sl.item_id = rm.id
        WHERE sl.item_type = 'MP' 
        AND rm.status = 'ativo'
        AND sl.qty > 0
        AND sl.avg_cost IS NOT NULL
        """)
    elif item_type == "PA":
        # Only calculate for active products
        query = text("""
        SELECT sl.qty, sl.avg_cost
        FROM stocklot sl
        INNER JOIN product p ON sl.item_id = p.id
        WHERE sl.item_type = 'PA' 
        AND p.status = 'ativo'
        AND sl.qty > 0
        AND sl.avg_cost IS NOT NULL
        """)
    else:
        # Calculate for both active raw materials and products
        query = text("""
        SELECT sl.qty, sl.avg_cost
        FROM stocklot sl
        LEFT JOIN rawmaterial rm ON sl.item_id = rm.id AND sl.item_type = 'MP'
        LEFT JOIN product p ON sl.item_id = p.id AND sl.item_type = 'PA'
        WHERE sl.qty > 0
        AND sl.avg_cost IS NOT NULL
        AND (
            (sl.item_type = 'MP' AND rm.status = 'ativo') OR
            (sl.item_type = 'PA' AND p.status = 'ativo')
        )
        """)

    results = session.exec(query).all()

    total_value = 0.0
    total_qty = 0.0

    for qty, avg_cost in results:
        if avg_cost and qty > 0:
            total_value += qty * avg_cost
            total_qty += qty

    return {
        "total_value": total_value,
        "total_qty": total_qty,
        "lot_count": len(results)
    }

def mrp_requirements(session: Session, product_id: int, required_units: float) -> List[dict]:
    """Calculate MRP requirements for a product based on units to produce"""
    # Get approved formulation for product
    formulation = session.exec(
        select(Formulation)
        .where(Formulation.product_id == product_id)
        .where(Formulation.state == "Aprovado/Em Uso")
    ).first()

    if not formulation:
        return []

    # Get product info to calculate proportion
    product = session.get(Product, product_id)
    if not product:
        return []

    # Calculate how many units are produced per standard batch
    # std_batch_weight is the total weight of one batch
    # unit_weight is the weight of one unit
    if product.unit_weight > 0:
        units_per_batch = product.std_batch_weight / product.unit_weight
    else:
        # Fallback: assume 1 unit per batch if unit_weight is not set
        units_per_batch = 1.0

    # Calculate proportion based on required units vs units per batch
    proportion = required_units / units_per_batch if units_per_batch > 0 else 1.0

    # Get formulation items
    items = session.exec(select(FormulaItem).where(FormulaItem.formulation_id == formulation.id)).all()

    requirements = []

    for item in items:
        rm = session.get(RawMaterial, item.raw_material_id)
        if rm:
            # Calculate required quantity proportionally
            # item.qty is the amount needed for one standard batch (units_per_batch units)
            required_rm_qty = item.qty * proportion

            # Get available stock (only approved lots with quantity > 0)
            available_stock = session.exec(
                select(StockLot)
                .where(StockLot.item_type == "MP")
                .where(StockLot.item_id == rm.id)
                .where(StockLot.status == "Aprovado")
                .where(StockLot.qty > 0)
            ).all()

            # Convert stock quantities to formulation unit
            total_available_converted = 0.0
            for lot in available_stock:
                # Convert lot quantity to formulation unit
                lot_qty_converted = convert_units(lot.qty, lot.uom, item.uom, rm)
                total_available_converted += lot_qty_converted

            # Calculate net requirement
            net_requirement = max(0, required_rm_qty - total_available_converted)

            requirements.append({
                "raw_material_id": rm.id,
                "raw_material_code": rm.code,
                "raw_material_name": rm.name_usual,
                "required_qty": required_rm_qty,
                "available_qty": total_available_converted,
                "net_requirement": net_requirement,
                "uom": item.uom,
                "proportion_factor": proportion,
                "units_per_batch": units_per_batch,
                "required_units": required_units
            })

    return requirements

def convert_units(qty: float, from_uom: str, to_uom: str, rm: RawMaterial) -> float:
    """Convert quantity from one unit to another for a raw material"""
    # Normalize unit strings for comparison
    from_unit = from_uom.upper().strip()
    to_unit = to_uom.upper().strip()

    # If units are the same, no conversion needed
    if from_unit == to_unit:
        return qty

    # Convert weight units
    if from_unit == "KG" and to_unit in ["G", "GRAMAS", "GRAMA"]:
        return qty * 1000  # Convert kg to grams
    elif from_unit in ["G", "GRAMAS", "GRAMA"] and to_unit == "KG":
        return qty / 1000  # Convert grams to kg

    # Convert volume units
    elif from_unit == "L" and to_unit in ["ML", "MILILITRO", "MILILITROS"]:
        return qty * 1000  # Convert liters to ml
    elif from_unit in ["ML", "MILILITRO", "MILILITROS"] and to_unit == "L":
        return qty / 1000  # Convert ml to liters

    # Apply density conversion if needed for mass/volume conversions
    elif rm.density:
        # Convert using density
        if from_unit in ["KG", "G"] and to_unit in ["L", "ML", "LITRO", "LITROS", "MILILITRO", "MILILITROS"]:
            # Convert mass to volume using density
            mass_in_kg = qty if from_unit == "KG" else qty / 1000
            volume_in_liters = mass_in_kg / rm.density

            if to_unit in ["ML", "MILILITRO", "MILILITROS"]:
                return volume_in_liters * 1000
            else:
                return volume_in_liters

        elif from_unit in ["L", "ML", "LITRO", "LITROS", "MILILITRO", "MILILITROS"] and to_unit in ["KG", "G"]:
            # Convert volume to mass using density
            volume_in_liters = qty if from_unit in ["L", "LITRO", "LITROS"] else qty / 1000
            mass_in_kg = volume_in_liters * rm.density

            if to_unit == "G":
                return mass_in_kg * 1000
            else:
                return mass_in_kg

    # If no conversion rule matches, return original quantity
    # This handles cases where units might be the same but written differently
    return qty

def check_expiring_lots(session: Session, days_ahead: int = 30) -> List[StockLot]:
    """Find lots expiring within specified days"""
    from datetime import timedelta

    cutoff_date = date.today() + timedelta(days=days_ahead)

    expiring_lots = session.exec(
        select(StockLot)
        .where(StockLot.expiry.isnot(None))
        .where(StockLot.expiry <= cutoff_date)
        .where(StockLot.status == "Aprovado")
        .where(StockLot.qty > 0)
    ).all()

    return list(expiring_lots)

def calculate_inventory_turnover(session: Session, item_type: str, days: int = 365) -> dict:
    """Calculate inventory turnover metrics"""
    # This is a simplified calculation
    # In a real system, you'd track consumption/usage over time

    current_stock = calculate_stock_value(session, item_type)

    # Placeholder calculation - would need historical data
    estimated_annual_usage = current_stock["total_value"] * 6  # Assuming 6x turnover

    turnover_ratio = estimated_annual_usage / current_stock["total_value"] if current_stock["total_value"] > 0 else 0
    days_of_supply = 365 / turnover_ratio if turnover_ratio > 0 else 0

    return {
        "turnover_ratio": turnover_ratio,
        "days_of_supply": days_of_supply,
        "current_value": current_stock["total_value"]
    }

def consume_raw_materials_from_stock(session: Session, product_id: int, produced_units: float) -> dict:
    """
    Automatically consume raw materials from stock when a production order is completed.
    Uses FEFO (First Expired, First Out) logic to select lots for consumption.
    
    Returns a dictionary with consumption details and any issues.
    """
    from models import Formulation, FormulaItem, Product, RawMaterial, StockLot
    from datetime import date
    
    # Get approved formulation for the product
    formulation = session.exec(
        select(Formulation)
        .where(Formulation.product_id == product_id)
        .where(Formulation.state == "Aprovado/Em Uso")
    ).first()
    
    if not formulation:
        return {
            "success": False,
            "error": "Produto não possui formulação aprovada",
            "consumptions": []
        }
    
    # Get product info to calculate proportion
    product = session.get(Product, product_id)
    if not product:
        return {
            "success": False,
            "error": "Produto não encontrado",
            "consumptions": []
        }
    
    # Calculate proportion based on produced units
    if product.unit_weight > 0:
        units_per_batch = product.std_batch_weight / product.unit_weight
    else:
        units_per_batch = 1.0
    
    proportion = produced_units / units_per_batch if units_per_batch > 0 else 1.0
    
    # Get formulation items
    items = session.exec(
        select(FormulaItem, RawMaterial)
        .join(RawMaterial, FormulaItem.raw_material_id == RawMaterial.id)
        .where(FormulaItem.formulation_id == formulation.id)
    ).all()
    
    consumptions = []
    issues = []
    
    for formula_item, raw_material in items:
        # Calculate required quantity for this production
        required_qty = formula_item.qty * proportion
        
        # Get available stock lots for this raw material (only approved lots with qty > 0)
        available_lots = session.exec(
            select(StockLot)
            .where(StockLot.item_type == "MP")
            .where(StockLot.item_id == raw_material.id)
            .where(StockLot.status == "Aprovado")
            .where(StockLot.qty > 0)
        ).all()
        
        if not available_lots:
            issues.append(f"Sem estoque disponível para {raw_material.code} - {raw_material.name_usual}")
            continue
        
        # Convert all lot quantities to the formulation unit for proper calculation
        lots_with_converted_qty = []
        for lot in available_lots:
            converted_qty = convert_units(lot.qty, lot.uom, formula_item.uom, raw_material)
            if converted_qty > 0:  # Only include lots with convertible quantities
                lots_with_converted_qty.append({
                    "lot": lot,
                    "converted_qty": converted_qty,
                    "original_qty": lot.qty,
                    "original_uom": lot.uom
                })
        
        if not lots_with_converted_qty:
            issues.append(f"Sem estoque conversível para {raw_material.code} - {raw_material.name_usual}")
            continue
        
        # Sort by FEFO (First Expired, First Out) - lots with earlier expiry dates first
        lots_with_converted_qty.sort(key=lambda x: (x["lot"].expiry or date.max, x["lot"].id))
        
        # Calculate total available in formulation units
        total_available = sum(item["converted_qty"] for item in lots_with_converted_qty)
        
        if total_available < required_qty:
            issues.append(f"Estoque insuficiente para {raw_material.code}: necessário {required_qty:.3f} {formula_item.uom}, disponível {total_available:.3f} {formula_item.uom}")
            # Even with insufficient stock, consume what's available
            if total_available > 0:
                st.warning(f"⚠️ Consumindo apenas o disponível para {raw_material.code}: {total_available:.3f} {formula_item.uom}")
                required_qty = total_available  # Adjust to consume only what's available
            else:
                continue  # Skip if no stock available
        
        # Consume from lots using FEFO
        remaining_to_consume = required_qty
        lot_consumptions = []
        
        for lot_info in lots_with_converted_qty:
            if remaining_to_consume <= 0:
                break
            
            lot = lot_info["lot"]
            available_in_formula_unit = lot_info["converted_qty"]
            
            # Determine how much to consume from this lot
            consume_in_formula_unit = min(remaining_to_consume, available_in_formula_unit)
            
            # Convert back to the lot's original unit for stock deduction
            consume_in_lot_unit = convert_units(consume_in_formula_unit, formula_item.uom, lot.uom, raw_material)
            
            # Update lot quantity
            lot.qty -= consume_in_lot_unit
            if lot.qty < 0:  # Prevent negative quantities due to conversion rounding
                lot.qty = 0
            
            lot_consumptions.append({
                "lot_code": lot.lot_code,
                "consumed_qty": consume_in_lot_unit,
                "consumed_uom": lot.uom,
                "remaining_qty": lot.qty
            })
            
            remaining_to_consume -= consume_in_formula_unit
        
        consumptions.append({
            "raw_material_code": raw_material.code,
            "raw_material_name": raw_material.name_usual,
            "required_qty": required_qty,
            "required_uom": formula_item.uom,
            "lot_consumptions": lot_consumptions
        })
    
    # Commit changes to database
    session.commit()
    
    return {
        "success": len(issues) == 0,
        "consumptions": consumptions,
        "issues": issues,
        "produced_units": produced_units,
        "proportion_used": proportion
    }