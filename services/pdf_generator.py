
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

def generate_purchase_order_pdf(purchase_order, supplier, items, order_type="Pedido de Compra"):
    """
    Gera um PDF formal de pedido de compra ou pedido de amostra
    
    Args:
        purchase_order: Objeto PurchaseOrder com os dados do pedido
        supplier: Objeto Supplier com dados do fornecedor
        items: Lista de tuplas (PurchaseItem, código_mp, nome_mp)
        order_type: Tipo do pedido ("Pedido de Compra" ou "Pedido de Amostra")
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    # Criar diretório temporário se não existir
    os.makedirs("temp", exist_ok=True)
    
    # Nome do arquivo baseado no tipo de pedido
    file_prefix = "Pedido_Compra" if order_type == "Pedido de Compra" else "Pedido_Amostra"
    filename = f"temp/{file_prefix}_{purchase_order.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Criar documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para elementos do PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo do subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Cabeçalho da empresa com logo
    logo_path = "attached_assets/WhatsApp Image 2025-10-22 at 16.59.19_1761163206748.jpeg"
    
    if os.path.exists(logo_path):
        try:
            # Adicionar logo com tamanho controlado
            logo = Image(logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            # Se houver erro ao carregar a imagem, continua sem ela
            print(f"Erro ao carregar logo: {e}")
    
    # Título do pedido baseado no tipo
    title_text = order_type.upper()
    story.append(Paragraph(title_text, subtitle_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Dados do pedido
    data_pedido = [
        ["Código do Pedido:", purchase_order.code],
        ["Fornecedor:", supplier.name],
        ["Data do Pedido:", purchase_order.order_date.strftime("%d/%m/%Y") if purchase_order.order_date else ""],
        ["Status:", purchase_order.status],
        ["Condições de Pagamento:", purchase_order.payment_terms or "N/A"]
    ]
    
    table_info = Table(data_pedido, colWidths=[5*cm, 10*cm])
    table_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4A6B')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table_info)
    story.append(Spacer(1, 0.5*cm))
    
    # Tabela de itens do pedido
    story.append(Paragraph("<b>Itens do Pedido:</b>", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Cabeçalho da tabela
    items_data = [[
        "#", 
        "Matéria-Prima", 
        "Quantidade", 
        "Unidade", 
        "Valor Total",
        "Data Entrega"
    ]]
    
    # Adicionar dados dos itens
    total_value = 0
    for idx, (item, rm_code, rm_name) in enumerate(items, 1):
        line_total = item.price  # Price is already the total value
        total_value += line_total
        
        items_data.append([
            str(idx),
            rm_name,
            f"{item.qty:.2f}",
            item.uom,
            f"R$ {item.price:.2f}",
            item.due_date.strftime("%d/%m/%Y") if item.due_date else "N/A"
        ])
    
    # Larguras das colunas
    table_items = Table(
        items_data, 
        colWidths=[0.8*cm, 6.5*cm, 2.5*cm, 2*cm, 3*cm, 2.7*cm]
    )
    
    table_items.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),     # Nome da Matéria-Prima
        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),  # Restante centralizado
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
    ]))
    
    story.append(table_items)
    story.append(Spacer(1, 0.5*cm))
    
    # Valor total
    total_table_data = [
        ["VALOR TOTAL DO PEDIDO:", f"R$ {total_value:.2f}"]
    ]
    
    total_table = Table(total_table_data, colWidths=[12*cm, 4.5*cm])
    total_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('ALIGN', (0, 0), (0, 0), 'RIGHT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#2E4A6B')),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
    ]))
    
    story.append(total_table)
    story.append(Spacer(1, 1*cm))
    
    # Rodapé
    texto_rodape = ""
    story.append(Paragraph(texto_rodape, normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    texto_empresa = "<b>GARNET COSMÉTICOS</b>"
    story.append(Paragraph(texto_empresa, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informações de contato
    texto_contato = """
    <b>Contato:</b><br/>
    📧 Email: faleconosco@garnetcosmeticos.com.br<br/>
    📱 WhatsApp: 11 98153-1188
    """
    story.append(Paragraph(texto_contato, normal_style))
    
    # Gerar PDF
    doc.build(story)
    
    return filename


def generate_quote_request_pdf(quote_request, supplier, items):
    """
    Gera um PDF formal de solicitação de orçamento
    
    Args:
        quote_request: Objeto QuoteRequest com os dados da solicitação
        supplier: Objeto Supplier com dados do fornecedor
        items: Lista de QuoteRequestItem
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    # Criar diretório temporário se não existir
    os.makedirs("temp", exist_ok=True)
    
    # Nome do arquivo
    filename = f"temp/Solicitacao_Orcamento_{quote_request.request_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Criar documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para elementos do PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo do subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Cabeçalho da empresa com logo
    logo_path = "attached_assets/WhatsApp Image 2025-10-22 at 16.59.19_1761163206748.jpeg"
    
    if os.path.exists(logo_path):
        try:
            # Adicionar logo com tamanho controlado
            logo = Image(logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            # Se houver erro ao carregar a imagem, continua sem ela
            print(f"Erro ao carregar logo: {e}")
    
    # Título da solicitação
    story.append(Paragraph("SOLICITAÇÃO DE ORÇAMENTO", subtitle_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Dados da solicitação
    data_solicitacao = [
        ["Número da Solicitação:", quote_request.request_number],
        ["Data:", quote_request.request_date.strftime("%d/%m/%Y") if quote_request.request_date else ""],
        ["Status:", quote_request.status]
    ]
    
    table_info = Table(data_solicitacao, colWidths=[5*cm, 10*cm])
    table_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4A6B')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table_info)
    story.append(Spacer(1, 0.5*cm))
    
    # Texto de solicitação
    texto_solicitacao = f"Prezado(a) fornecedor(a) <b>{supplier.name}</b>,"
    story.append(Paragraph(texto_solicitacao, normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    texto_corpo = "Solicitamos orçamento para os seguintes itens:"
    story.append(Paragraph(texto_corpo, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Tabela consolidada com todas as informações
    # Cabeçalho: #, Produto, INCI NAME, Quantidade, Unidade, EMBALAGEM MÍNIMA, PREÇO, VALIDADE, LEAD TIME
    consolidated_data = [[
        "#", 
        "Produto", 
        "INCI NAME", 
        "Quantidade", 
        "Unidade", 
        "EMBALAGEM\nMÍNIMA", 
        "PREÇO", 
        "VALIDADE", 
        "LEAD TIME"
    ]]
    
    # Criar estilo para texto pequeno com quebra de linha
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=7,
        leading=9,
        alignment=TA_LEFT
    )
    
    # Adicionar dados dos itens com campos vazios para preenchimento do fornecedor
    for idx, item in enumerate(items, 1):
        # Criar Paragraph para item_name e chemical_name para permitir quebra de linha
        item_name_paragraph = Paragraph(item.item_name, small_style)
        chemical_name_paragraph = Paragraph(item.chemical_name or "", small_style) if item.chemical_name else ""
        
        consolidated_data.append([
            str(idx),
            item_name_paragraph,
            chemical_name_paragraph,
            str(item.min_quantity),
            item.uom,
            "",  # EMBALAGEM MÍNIMA - para fornecedor preencher
            "",  # PREÇO - para fornecedor preencher
            "",  # VALIDADE - para fornecedor preencher
            ""   # LEAD TIME - para fornecedor preencher
        ])
    
    # Larguras das colunas ajustadas para A4 (largura útil ~17cm)
    table_consolidated = Table(
        consolidated_data, 
        colWidths=[0.8*cm, 3.2*cm, 3*cm, 1.8*cm, 1.3*cm, 2.2*cm, 1.8*cm, 1.8*cm, 1.6*cm]
    )
    
    table_consolidated.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),     # Produto e INCI NAME
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'),  # Restante centralizado
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),    # Alinhamento vertical superior
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Padding - Ajustado para acomodar quebras de linha
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Zebra striping para facilitar leitura
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        
        # Destaque visual para campos a preencher (colunas 5-8)
        ('BACKGROUND', (5, 1), (-1, -1), colors.HexColor('#FFFEF0')),
        
        # Quebra de linha
        ('WORDWRAP', (0, 0), (-1, -1), True),
    ]))
    
    story.append(table_consolidated)
    story.append(Spacer(1, 0.7*cm))
    
    # Observações
    if quote_request.notes:
        story.append(Paragraph("<b>Observações:</b>", normal_style))
        story.append(Paragraph(quote_request.notes, normal_style))
        story.append(Spacer(1, 0.5*cm))
    
    # Rodapé
    story.append(Spacer(1, 1*cm))
    texto_rodape = "Aguardamos seu retorno."
    story.append(Paragraph(texto_rodape, normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    texto_atenciosamente = "Obrigado! <br/><b>GARNET COSMÉTICOS</b>"
    story.append(Paragraph(texto_atenciosamente, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informações de contato
    texto_contato = """
    <b>Contato:</b><br/>
    📧 Email: faleconosco@garnetcosmeticos.com.br<br/>
    📱 WhatsApp: 11 98153-1188
    """
    story.append(Paragraph(texto_contato, normal_style))

    
    # Gerar PDF
    doc.build(story)
    
    return filename



def generate_stock_report_pdf(stock_items, user_role=None):
    """
    Gera um PDF formal de relatório de estoque
    
    Args:
        stock_items: Lista de dicionários com dados do estoque
        user_role: Role do usuário para determinar se mostra informações de custo
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    # Criar diretório temporário se não existir
    os.makedirs("temp", exist_ok=True)
    
    # Nome do arquivo
    filename = f"temp/Relatorio_Estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Criar documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para elementos do PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Cabeçalho da empresa com logo
    logo_path = "attached_assets/WhatsApp Image 2025-10-22 at 16.59.19_1761163206748.jpeg"
    
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")
    
    # Título
    story.append(Paragraph("RELATÓRIO DE ESTOQUE DE MATÉRIAS-PRIMAS", subtitle_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Data do relatório
    data_info = f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    story.append(Paragraph(data_info, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Tabela de estoque
    story.append(Paragraph("<b>Itens em Estoque:</b>", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Cabeçalho da tabela - diferente para managers e operators
    if user_role == "manager":
        items_data = [[
            "#", 
            "Código MP",
            "Nome", 
            "Lote",
            "Quantidade",
            "UOM",
            "Validade",
            "Status",
            "Custo Médio",
            "Valor Total"
        ]]
    else:
        items_data = [[
            "#", 
            "Código MP",
            "Nome", 
            "Lote",
            "Quantidade",
            "UOM",
            "Validade",
            "Status",
            "Localização"
        ]]
    
    # Criar estilo para texto pequeno com quebra de linha
    small_style = ParagraphStyle(
        'SmallText',
        parent=styles['Normal'],
        fontSize=8,
        leading=10,
        alignment=TA_LEFT
    )
    
    # Adicionar dados dos itens
    total_value = 0
    for idx, item in enumerate(stock_items, 1):
        # Criar Paragraph para o nome (permite quebra de linha)
        nome_paragraph = Paragraph(item.get("Nome", ""), small_style)
        
        if user_role == "manager":
            # Extrair valor numérico do "Valor Total"
            valor_str = item.get("Valor Total", "R$ 0,00")
            valor_num = float(valor_str.replace("R$ ", "").replace(",", ""))
            total_value += valor_num
            
            items_data.append([
                str(idx),
                item.get("Código MP", ""),
                nome_paragraph,
                item.get("Lote", ""),
                f"{item.get('Quantidade', 0):.2f}",
                item.get("UOM", ""),
                item.get("Validade", "N/A"),
                item.get("Status", ""),
                item.get("Custo Médio", "N/A"),
                item.get("Valor Total", "N/A")
            ])
        else:
            items_data.append([
                str(idx),
                item.get("Código MP", ""),
                nome_paragraph,
                item.get("Lote", ""),
                f"{item.get('Quantidade', 0):.2f}",
                item.get("UOM", ""),
                item.get("Validade", "N/A"),
                item.get("Status", ""),
                item.get("Localização", "N/A")
            ])
    
    # Larguras das colunas - diferentes para managers e operators
    if user_role == "manager":
        table_stock = Table(
            items_data, 
            colWidths=[0.7*cm, 2*cm, 3.5*cm, 2*cm, 1.8*cm, 1.2*cm, 1.8*cm, 1.8*cm, 2*cm, 2*cm]
        )
    else:
        table_stock = Table(
            items_data, 
            colWidths=[0.8*cm, 2.2*cm, 4.5*cm, 2.2*cm, 2*cm, 1.4*cm, 2*cm, 1.8*cm, 2.5*cm]
        )
    
    table_stock.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Código
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Nome (com quebra de linha)
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Restante centralizado
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),   # Alinhamento vertical superior
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Padding - Ajustado para acomodar quebras de linha
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        
        # Permitir quebra de linha
        ('WORDWRAP', (2, 1), (2, -1), True),
    ]))
    
    story.append(table_stock)
    story.append(Spacer(1, 1*cm))
    
    # Resumo - apenas para managers
    if user_role == "manager":
        summary_data = [
            ["TOTAL DE ITENS:", str(len(stock_items))],
            ["VALOR TOTAL DO ESTOQUE:", f"R$ {total_value:,.2f}"]
        ]
        
        summary_table = Table(summary_data, colWidths=[12*cm, 5*cm])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2E4A6B')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0F0F0')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#2E4A6B')),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 1*cm))
    
    # Rodapé
    texto_empresa = "<b>GARNET COSMÉTICOS</b>"
    story.append(Paragraph(texto_empresa, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informações de contato
    texto_contato = """
    <b>Contato:</b><br/>
    📧 Email: faleconosco@garnetcosmeticos.com.br<br/>
    📱 WhatsApp: 11 98153-1188
    """
    story.append(Paragraph(texto_contato, normal_style))
    
    # Gerar PDF
    doc.build(story)
    
    return filename


def generate_production_order_pdf(production_order, product, requirements):
    """
    Gera um PDF formal de ordem de produção
    
    Args:
        production_order: Objeto ProductionOrder com os dados da ordem
        product: Objeto Product com dados do produto
        requirements: Lista de dicionários com necessidades de matéria-prima (do mrp_requirements)
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    # Criar diretório temporário se não existir
    os.makedirs("temp", exist_ok=True)
    
    # Nome do arquivo
    filename = f"temp/Ordem_Producao_{production_order.code}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Criar documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para elementos do PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Cabeçalho da empresa com logo
    logo_path = "attached_assets/WhatsApp Image 2025-10-22 at 16.59.19_1761163206748.jpeg"
    
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")
    
    # Título
    story.append(Paragraph("ORDEM DE PRODUÇÃO", subtitle_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Calculate proportional KG based on formulation
    if product.unit_weight > 0:
        units_per_batch = product.std_batch_weight / product.unit_weight
    else:
        units_per_batch = 1.0
    
    proportion = production_order.qty_to_produce / units_per_batch if units_per_batch > 0 else 1.0
    proportional_kg = (product.std_batch_weight * proportion) / 1000  # Convert g to kg
    
    qty_display = f"{production_order.qty_to_produce:.0f} unidades / {proportional_kg:.3f} kg"
    
    # Dados da ordem de produção
    data_op = [
        ["Código da Ordem:", production_order.code],
        ["Produto:", f"{product.code} - {product.name}"],
        ["Quantidade a Produzir:", qty_display],
        ["Lote Planejado:", production_order.planned_lot or "N/A"],
        ["Data Início:", production_order.start_date.strftime("%d/%m/%Y") if production_order.start_date else "N/A"],
        ["Data Fim:", production_order.end_date.strftime("%d/%m/%Y") if production_order.end_date else "N/A"],
        ["Status:", production_order.status],
        ["Criado Por:", production_order.created_by or "N/A"],
        ["Data de Criação:", production_order.created_at.strftime("%d/%m/%Y %H:%M") if production_order.created_at else "N/A"]
    ]
    
    table_info = Table(data_op, colWidths=[5*cm, 10*cm])
    table_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4A6B')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table_info)
    story.append(Spacer(1, 0.5*cm))
    
    # Tabela de necessidades de matéria-prima
    story.append(Paragraph("<b>Necessidades de Matéria-Prima:</b>", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    if requirements:
        # Criar estilo para cabeçalhos com quebra de linha
        header_style = ParagraphStyle(
            'HeaderText',
            parent=styles['Normal'],
            fontSize=8,
            leading=9,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold',
            textColor=colors.whitesmoke
        )
        
        # Cabeçalho da tabela com Paragraphs para quebra de linha
        items_data = [[
            Paragraph("#", header_style), 
            Paragraph("Código<br/>MP", header_style),
            Paragraph("Matéria-Prima", header_style), 
            Paragraph("Necessário<br/>(KG)", header_style), 
            Paragraph("Disponível<br/>(KG)", header_style),
            Paragraph("Necessidade<br/>Líquida (KG)", header_style),
            Paragraph("Status", header_style)
        ]]
        
        # Criar estilo para texto pequeno com quebra de linha
        small_style = ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT
        )
        
        # Adicionar dados dos itens
        for idx, req in enumerate(requirements, 1):
            # Converter quantidades para KG para exibição
            def convert_to_kg(qty, original_unit):
                if original_unit in ["G", "GRAMAS", "GRAMA"]:
                    return qty / 1000
                elif original_unit in ["KG"]:
                    return qty
                elif original_unit in ["L", "LITRO", "LITROS"]:
                    return qty  # Assuming density ~1
                elif original_unit in ["ML", "MILILITRO", "MILILITROS"]:
                    return qty / 1000
                else:
                    return qty
            
            required_kg = convert_to_kg(req['required_qty'], req['uom'])
            available_kg = convert_to_kg(req['available_qty'], req['uom'])
            net_requirement_kg = convert_to_kg(req['net_requirement'], req['uom'])
            
            # Status message
            status = "✅ OK" if req["net_requirement"] == 0 else f"⚠️ Falta"
            
            # Criar Paragraph para o nome da matéria-prima
            rm_name_paragraph = Paragraph(req["raw_material_name"], small_style)
            
            items_data.append([
                str(idx),
                req["raw_material_code"],
                rm_name_paragraph,
                f"{required_kg:.3f}",
                f"{available_kg:.3f}",
                f"{net_requirement_kg:.3f}" if net_requirement_kg > 0 else "0",
                status
            ])
        
        # Larguras das colunas
        table_items = Table(
            items_data, 
            colWidths=[0.7*cm, 2*cm, 5*cm, 2.5*cm, 2.5*cm, 2.8*cm, 1.8*cm]
        )
        
        table_items.setStyle(TableStyle([
            # Cabeçalho
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            
            # Corpo da tabela
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
            ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Código MP
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Nome (com quebra de linha)
            ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Restante centralizado
            ('VALIGN', (0, 1), (-1, -1), 'TOP'),   # Alinhamento vertical superior
            
            # Bordas
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            
            # Padding
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            
            # Zebra striping
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
            
            # Permitir quebra de linha
            ('WORDWRAP', (2, 1), (2, -1), True),
        ]))
        
        story.append(table_items)
        story.append(Spacer(1, 0.5*cm))
        
        # Informação sobre o cálculo
        if requirements:
            units_per_batch = requirements[0]["units_per_batch"]
            proportion = requirements[0]["proportion_factor"]
            calc_info = f"💡 Cálculo baseado em: {production_order.qty_to_produce:.0f} unidades ÷ {units_per_batch:.0f} unidades/lote = {proportion:.3f}x a formulação"
            story.append(Paragraph(calc_info, normal_style))
            story.append(Spacer(1, 1*cm))
    else:
        story.append(Paragraph("Produto sem formulação aprovada ou sem necessidades calculadas.", normal_style))
        story.append(Spacer(1, 1*cm))
    
    # Rodapé
    texto_empresa = "<b>GARNET COSMÉTICOS</b>"
    story.append(Paragraph(texto_empresa, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informações de contato
    texto_contato = """
    <b>Contato:</b><br/>
    📧 Email: faleconosco@garnetcosmeticos.com.br<br/>
    📱 WhatsApp: 11 98153-1188
    """
    story.append(Paragraph(texto_contato, normal_style))
    
    # Gerar PDF
    doc.build(story)
    
    return filename


def generate_formulation_pdf(formulation, product, items, user_role=None):
    """
    Gera um PDF formal de formulação de produto
    
    Args:
        formulation: Objeto Formulation com os dados da formulação
        product: Objeto Product com dados do produto
        items: Lista de tuplas (FormulaItem, código_mp, nome_mp, preço_mp, supplier_id, supplier_name)
        user_role: Role do usuário para determinar se mostra informações de custo
    
    Returns:
        str: Caminho do arquivo PDF gerado
    """
    # Criar diretório temporário se não existir
    os.makedirs("temp", exist_ok=True)
    
    # Nome do arquivo
    filename = f"temp/Formulacao_{product.code}_{formulation.version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    # Criar documento
    doc = SimpleDocTemplate(filename, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    # Container para elementos do PDF
    story = []
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do título
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo do subtítulo
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#2E4A6B'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo normal
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_LEFT
    )
    
    # Cabeçalho da empresa com logo
    logo_path = "attached_assets/WhatsApp Image 2025-10-22 at 16.59.19_1761163206748.jpeg"
    
    if os.path.exists(logo_path):
        try:
            # Adicionar logo com tamanho controlado
            logo = Image(logo_path, width=4*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            # Se houver erro ao carregar a imagem, continua sem ela
            print(f"Erro ao carregar logo: {e}")
    
    # Título
    story.append(Paragraph("FORMULAÇÃO DE PRODUTO", subtitle_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Dados da formulação
    data_formulacao = [
        ["Produto:", f"{product.code} - {product.name}"],
        ["Versão:", formulation.version],
        ["Estado:", formulation.state],
        ["Lote Padrão:", f"{product.std_batch_weight} g"],
        ["Peso Unitário:", f"{product.unit_weight} {product.unit_uom}"]
    ]
    
    if formulation.approved_by:
        data_formulacao.append(["Aprovado Por:", formulation.approved_by])
    if formulation.approved_at:
        data_formulacao.append(["Data Aprovação:", formulation.approved_at.strftime("%d/%m/%Y")])
    
    table_info = Table(data_formulacao, colWidths=[5*cm, 10*cm])
    table_info.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4A6B')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    story.append(table_info)
    story.append(Spacer(1, 0.5*cm))
    
    # Tabela de composição
    story.append(Paragraph("<b>Composição da Formulação:</b>", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Cabeçalho da tabela - diferente para managers
    if user_role == "manager":
        items_data = [[
            "#", 
            "Código MP",
            "Matéria-Prima", 
            "Qtd.", 
            "Un.", 
            "Preço Base",
            "% Form.",
            "Custo"
        ]]
    else:
        items_data = [[
            "#", 
            "Código MP",
            "Matéria-Prima", 
            "Qtd.", 
            "Un.", 
            "% Form."
        ]]
    
    # Adicionar dados dos itens usando Paragraph para quebra de linha automática
    for idx, (item, rm_code, rm_name, rm_price, supplier_id, supplier_name) in enumerate(items, 1):
        # Calcular percentual
        item_qty_in_grams = item.qty
        if item.uom == "KG":
            item_qty_in_grams = item.qty * 1000
        elif item.uom == "L":
            item_qty_in_grams = item.qty * 1000
        elif item.uom == "ML":
            item_qty_in_grams = item.qty * 1
        
        percentage = (item_qty_in_grams / product.std_batch_weight * 100) if product.std_batch_weight > 0 else 0
        
        # Criar Paragraph para o nome da matéria-prima (permite quebra de linha)
        small_style = ParagraphStyle(
            'SmallText',
            parent=styles['Normal'],
            fontSize=8,
            leading=10,
            alignment=TA_LEFT
        )
        rm_name_paragraph = Paragraph(rm_name, small_style)
        
        # Calcular custo do item para managers
        if user_role == "manager":
            from services.business import material_cost_unit
            from sqlmodel import Session
            from db import engine
            from models import RawMaterial
            
            with Session(engine) as session:
                rm = session.get(RawMaterial, item.raw_material_id)
                item_cost = material_cost_unit(rm, item.qty, item.uom)
            
            # Obter base_unit da matéria-prima
            with Session(engine) as session:
                rm = session.get(RawMaterial, item.raw_material_id)
                base_unit = rm.base_unit if rm else "UN"
            
            items_data.append([
                str(idx),
                rm_code,
                rm_name_paragraph,  # Usar Paragraph aqui
                f"{item.qty:.4f}",
                item.uom,
                f"R$ {rm_price:.2f}/{base_unit}",
                f"{percentage:.2f}%",
                f"R$ {item_cost:.2f}"
            ])
        else:
            items_data.append([
                str(idx),
                rm_code,
                rm_name_paragraph,  # Usar Paragraph aqui
                f"{item.qty:.4f}",
                item.uom,
                f"{percentage:.2f}%"
            ])
    
    # Larguras das colunas - diferentes para managers
    if user_role == "manager":
        table_items = Table(
            items_data, 
            colWidths=[0.7*cm, 1.8*cm, 5*cm, 1.6*cm, 1.2*cm, 2.2*cm, 1.8*cm, 1.8*cm]
        )
    else:
        table_items = Table(
            items_data, 
            colWidths=[0.8*cm, 2.2*cm, 7.5*cm, 1.8*cm, 1.5*cm, 2.5*cm]
        )
    
    table_items.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
        ('ALIGN', (1, 1), (1, -1), 'CENTER'),  # Código MP
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Nome (com quebra de linha)
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Restante centralizado
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),   # Alinhamento vertical superior
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        
        # Padding - Ajustado para acomodar quebras de linha
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        
        # Permitir quebra de linha
        ('WORDWRAP', (2, 1), (2, -1), True),
    ]))
    
    story.append(table_items)
    story.append(Spacer(1, 1.5*cm))
    
    # Rodapé - sem mensagem de confidencialidade
    if hasattr(formulation, 'notes') and formulation.notes:
        texto_rodape = f"<b>Observações:</b><br/>{formulation.notes}"
        story.append(Paragraph(texto_rodape, normal_style))
        story.append(Spacer(1, 0.5*cm))
    
    texto_empresa = "<b>GARNET COSMÉTICOS</b>"
    story.append(Paragraph(texto_empresa, normal_style))
    story.append(Spacer(1, 0.5*cm))
    
    # Informações de contato
    texto_contato = """
    <b>Contato:</b><br/>
    📧 Email: faleconosco@garnetcosmeticos.com.br<br/>
    📱 WhatsApp: 11 98153-1188
    """
    story.append(Paragraph(texto_contato, normal_style))
    
    # Gerar PDF
    doc.build(story)
    
    return filename
