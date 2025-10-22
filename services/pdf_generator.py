
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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
    
    # Cabeçalho da empresa
    story.append(Paragraph("GARNET INDÚSTRIA DE COSMÉTICOS LTDA", title_style))
    story.append(Spacer(1, 0.5*cm))
    
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
    items_data = [["#", "Tipo", "Nome do Item", "Nome Químico", "Nome Comercial", "Quantidade"]]
    
    for idx, item in enumerate(items, 1):
        items_data.append([
            str(idx),
            item.item_type,
            item.item_name,
            item.chemical_name or "-",
            item.commercial_name or "-",
            str(item.quantity)
        ])
    
    table_items = Table(items_data, colWidths=[1*cm, 2.5*cm, 3.5*cm, 3*cm, 3*cm, 2*cm])
    table_items.setStyle(TableStyle([
        # Cabeçalho
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4A6B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        
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
