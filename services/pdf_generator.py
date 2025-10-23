
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
        "Preço Unit.", 
        "Total",
        "Data Entrega"
    ]]
    
    # Adicionar dados dos itens
    total_value = 0
    for idx, (item, rm_code, rm_name) in enumerate(items, 1):
        line_total = item.qty * item.price
        total_value += line_total
        
        items_data.append([
            str(idx),
            rm_name,
            f"{item.qty:.2f}",
            item.uom,
            f"R$ {item.price:.2f}",
            f"R$ {line_total:.2f}",
            item.due_date.strftime("%d/%m/%Y") if item.due_date else "N/A"
        ])
    
    # Larguras das colunas
    table_items = Table(
        items_data, 
        colWidths=[0.8*cm, 5.5*cm, 2*cm, 1.5*cm, 2.2*cm, 2.2*cm, 2.3*cm]
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
    
    # Adicionar dados dos itens com campos vazios para preenchimento do fornecedor
    for idx, item in enumerate(items, 1):
        consolidated_data.append([
            str(idx),
            item.item_name,
            item.chemical_name or "",
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
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Coluna #
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),     # Produto e INCI NAME
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'),  # Restante centralizado
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        
        # Zebra striping para facilitar leitura
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
        
        # Destaque visual para campos a preencher (colunas 5-8)
        ('BACKGROUND', (5, 1), (-1, -1), colors.HexColor('#FFFEF0')),
        
        # Quebra de linha no cabeçalho
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
    
    # Adicionar dados dos itens
    total_value = 0
    for idx, item in enumerate(stock_items, 1):
        if user_role == "manager":
            # Extrair valor numérico do "Valor Total"
            valor_str = item.get("Valor Total", "R$ 0,00")
            valor_num = float(valor_str.replace("R$ ", "").replace(",", ""))
            total_value += valor_num
            
            items_data.append([
                str(idx),
                item.get("Código MP", ""),
                item.get("Nome", ""),
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
                item.get("Nome", ""),
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
        ('ALIGN', (1, 1), (2, -1), 'LEFT'),    # Código e Nome
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Restante centralizado
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
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
            "Quantidade", 
            "Unidade", 
            "Preço Base",
            "% Formulação",
            "Custo"
        ]]
    else:
        items_data = [[
            "#", 
            "Código MP",
            "Matéria-Prima", 
            "Quantidade", 
            "Unidade", 
            "% Formulação"
        ]]
    
    # Adicionar dados dos itens
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
                rm_name,
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
                rm_name,
                f"{item.qty:.4f}",
                item.uom,
                f"{percentage:.2f}%"
            ])
    
    # Larguras das colunas - diferentes para managers
    if user_role == "manager":
        table_items = Table(
            items_data, 
            colWidths=[0.8*cm, 2.2*cm, 4.8*cm, 1.9*cm, 1.4*cm, 2.3*cm, 2.1*cm, 2*cm]
        )
    else:
        table_items = Table(
            items_data, 
            colWidths=[1*cm, 2.8*cm, 6.5*cm, 2.2*cm, 1.8*cm, 2.7*cm]
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
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # Código MP
        ('ALIGN', (2, 1), (2, -1), 'LEFT'),    # Nome
        ('ALIGN', (3, 1), (-1, -1), 'CENTER'), # Restante centralizado
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding - Aumentado para melhor legibilidade
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
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
