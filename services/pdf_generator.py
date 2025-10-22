
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os

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
    
    # Tabela de itens
    items_data = [["#", "Tipo", "Nome do Item", "Nome Químico", "Nome Comercial", "Quantidade", "Unidade"]]
    
    for idx, item in enumerate(items, 1):
        items_data.append([
            str(idx),
            item.item_type,
            item.item_name,
            item.chemical_name or "-",
            item.commercial_name or "-",
            str(item.min_quantity),
            item.uom
        ])
    
    table_items = Table(items_data, colWidths=[1*cm, 2.2*cm, 3.5*cm, 3*cm, 3*cm, 2*cm, 1.8*cm])
    table_items.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('WORDWRAP', (0, 0), (-1, -1), True),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'LEFT'),
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        
        # Zebra striping
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F9FA')]),
    ]))
    
    story.append(table_items)
    story.append(Spacer(1, 0.7*cm))
    
    # Tabela para preenchimento do fornecedor
    story.append(Paragraph("<b>Para preenchimento do fornecedor:</b>", normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    # Cabeçalho da tabela de resposta do fornecedor
    supplier_response_data = [["#", "INCI NAME", "EMBALAGEM MÍNIMA", "PREÇO", "VALIDADE", "LEAD TIME"]]
    
    # Adicionar linhas vazias correspondentes aos itens solicitados
    for idx in range(1, len(items) + 1):
        supplier_response_data.append([
            str(idx),
            "",  # INCI NAME
            "",  # EMBALAGEM MÍNIMA
            "",  # PREÇO
            "",  # VALIDADE
            ""   # LEAD TIME
        ])
    
    table_supplier_response = Table(supplier_response_data, colWidths=[1*cm, 4*cm, 3.5*cm, 3*cm, 3*cm, 2*cm])
    table_supplier_response.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
        # Corpo da tabela
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        
        # Bordas
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Padding para facilitar o preenchimento
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        
        # Fundo branco para preenchimento
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ]))
    
    story.append(table_supplier_response)
    story.append(Spacer(1, 0.7*cm))
    
    # Observações
    if quote_request.notes:
        story.append(Paragraph("<b>Observações:</b>", normal_style))
        story.append(Paragraph(quote_request.notes, normal_style))
        story.append(Spacer(1, 0.5*cm))
    
    # Rodapé
    story.append(Spacer(1, 1*cm))
    texto_rodape = "Aguardamos seu retorno com a maior brevidade possível."
    story.append(Paragraph(texto_rodape, normal_style))
    story.append(Spacer(1, 0.3*cm))
    
    texto_atenciosamente = "Atenciosamente,<br/><b>GARNET Indústria de Cosméticos LTDA</b>"
    story.append(Paragraph(texto_atenciosamente, normal_style))
    
    # Gerar PDF
    doc.build(story)
    
    return filename
