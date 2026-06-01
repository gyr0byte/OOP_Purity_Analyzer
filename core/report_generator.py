import io
from datetime import datetime
from typing import Any
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf_report(analysis_dict: dict[str, Any], repos: list[dict[str, Any]]) -> bytes:
    """Generate a professional PDF analysis report using ReportLab.

    Args:
        analysis_dict: Serialized Analysis data.
        repos: List of serialized RepoResult data.

    Returns:
        Bytes of the generated PDF document.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom Palette
    c_primary = colors.HexColor("#0f172a")    # Slate 900
    c_accent = colors.HexColor("#6366f1")     # Indigo 500
    c_success = colors.HexColor("#10b981")    # Emerald 500
    c_warning = colors.HexColor("#f59e0b")    # Amber 500
    c_danger = colors.HexColor("#ef4444")     # Rose 500
    c_neutral_light = colors.HexColor("#f8fafc") # Slate 50
    c_border = colors.HexColor("#e2e8f0")

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=26,
        leading=30,
        textColor=c_primary,
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=30
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=c_accent,
        spaceBefore=15,
        spaceAfter=12,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_primary,
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )

    code_style = ParagraphStyle(
        'CodeStyleCustom',
        parent=styles['Code'],
        fontName='Courier',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        backColor=c_neutral_light,
        borderColor=c_border,
        borderWidth=1,
        borderPadding=6,
        spaceAfter=10
    )

    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=c_primary
    )

    story = []

    # Title & Header
    story.append(Paragraph("OOP Purity Analyzer v2.0", title_style))
    created_str = datetime.fromisoformat(analysis_dict["created_at"]).strftime("%B %d, %Y at %I:%M %p") if analysis_dict.get("created_at") else datetime.now().strftime("%B %d, %Y")
    story.append(Paragraph(f"Executive Analysis Report — Generated on {created_str}", subtitle_style))
    story.append(Spacer(1, 10))

    # Executive Summary Table
    story.append(Paragraph("Executive Summary", h1_style))
    
    summary_data = [
        [Paragraph("Analysis Property", table_header_style), Paragraph("Value / Details", table_header_style)],
        [Paragraph("Analysis Mode", table_cell_bold), Paragraph(analysis_dict.get("mode", "N/A").upper(), table_cell_style)],
        [Paragraph("Target Input Data", table_cell_bold), Paragraph(analysis_dict.get("input_data", "N/A"), table_cell_style)],
        [Paragraph("Total Repos Scraped", table_cell_bold), Paragraph(str(analysis_dict.get("total_repos", 0)), table_cell_style)],
        [Paragraph("Successfully Scored Repos", table_cell_bold), Paragraph(str(analysis_dict.get("scored_repos_count", 0)), table_cell_style)],
        [Paragraph("Unsupported/Skipped Repos", table_cell_bold), Paragraph(str(analysis_dict.get("unscored_repos_count", 0)), table_cell_style)],
    ]
    
    summary_table = Table(summary_data, colWidths=[2.2*inch, 5.0*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), c_primary),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, c_border),
        ('BACKGROUND', (0, 1), (0, -1), c_neutral_light),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Repositories Overview List Table
    story.append(Paragraph("Scored Repositories Overview", h1_style))
    
    overview_headers = [
        Paragraph("Repository Name", table_header_style),
        Paragraph("Dominant Lang", table_header_style),
        Paragraph("Purity Score", table_header_style),
        Paragraph("Purity Tier", table_header_style),
        Paragraph("Stars", table_header_style),
    ]
    
    overview_data = [overview_headers]
    for r in repos:
        score_val = f"{r.get('total_score', 'N/A')}/100" if r.get('scored') else "N/A"
        tier_val = r.get('purity_tier', 'Unsupported') if r.get('scored') else "Unsupported"
        
        # Color coding tier text
        tier_color = c_primary
        if "Pure OOP" in tier_val:
            tier_color = c_success
        elif "Near-Pure" in tier_val:
            tier_color = c_accent
        elif "Mixed" in tier_val:
            tier_color = c_warning
        elif "OOP-Adjacent" in tier_val or "Procedural" in tier_val:
            tier_color = c_danger

        tier_style = ParagraphStyle(
            'TierCol',
            parent=table_cell_bold,
            textColor=tier_color
        )

        overview_data.append([
            Paragraph(r.get("full_name", ""), table_cell_bold),
            Paragraph(r.get("matched_language") or r.get("primary_language", "Unknown"), table_cell_style),
            Paragraph(score_val, table_cell_bold),
            Paragraph(tier_val, tier_style),
            Paragraph(f"{r.get('stars', 0):,}", table_cell_style),
        ])

    overview_table = Table(overview_data, colWidths=[2.5*inch, 1.3*inch, 0.9*inch, 1.5*inch, 1.0*inch])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_accent),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_neutral_light]),
    ]))
    story.append(overview_table)
    story.append(PageBreak())

    # Detailed Repo Breakdown Pages
    story.append(Paragraph("Detailed Repository Insights", h1_style))
    story.append(Spacer(1, 10))

    for r in repos:
        repo_story = []
        repo_story.append(Paragraph(r.get("full_name", ""), h1_style))
        
        is_scored = r.get("scored", False)
        
        # Main stats block
        stat_lbl_style = ParagraphStyle('StatLbl', parent=body_style, fontName='Helvetica-Bold')
        
        summary_text = (
            f"<b>Primary Language:</b> {r.get('primary_language', 'N/A')}<br/>"
            f"<b>Popularity:</b> {r.get('stars', 0):,} stars | {r.get('forks', 0):,} forks<br/>"
            f"<b>Size:</b> {r.get('size_kb', 0):,} KB<br/>"
            f"<b>Status:</b> {'Scored successfully' if is_scored else 'Unscored / Language Unsupported'}<br/>"
        )
        if is_scored:
            summary_text += (
                f"<b>OOP Purity Score:</b> {r.get('total_score', 0)}/100<br/>"
                f"<b>Purity Tier:</b> {r.get('purity_tier', 'N/A')}<br/>"
            )
        else:
            summary_text += f"<b>Skipped Reason:</b> {r.get('reason', 'N/A')}<br/>"
            
        repo_story.append(Paragraph(summary_text, body_style))
        repo_story.append(Spacer(1, 10))

        if is_scored and r.get("languages_scored"):
            repo_story.append(Paragraph("AST Heuristic Structural Metrics", h2_style))
            
            # Show details per language scored
            for lang in r["languages_scored"]:
                m = lang.get("metrics") or {}
                m_data = [
                    [Paragraph("Metric", table_header_style), Paragraph("Value", table_header_style), Paragraph("Meaning", table_header_style)],
                    [Paragraph("Language", table_cell_bold), Paragraph(lang.get("language", "N/A"), table_cell_style), Paragraph("Scored source file language", table_cell_style)],
                    [Paragraph("Modifier Multiplier", table_cell_bold), Paragraph(f"{lang.get('modifier', 1.0)}x", table_cell_bold), Paragraph(lang.get("modifier_reason", "No adjustment"), table_cell_style)],
                    [Paragraph("Classes Discovered", table_cell_bold), Paragraph(str(m.get("class_count", 0)), table_cell_style), Paragraph("Total class declarations parsed", table_cell_style)],
                    [Paragraph("Inheritance Hierarchies", table_cell_bold), Paragraph(str(m.get("inheritance_count", 0)), table_cell_style), Paragraph("Child subclass relationships detected", table_cell_style)],
                    [Paragraph("Interfaces / Abstract", table_cell_bold), Paragraph(str(m.get("interface_count", 0) + m.get("abstract_count", 0)), table_cell_style), Paragraph("Interfaces or Abstract class templates", table_cell_style)],
                    [Paragraph("Encapsulated Members", table_cell_bold), Paragraph(f"Private: {m.get('private_members', 0)} | Protected: {m.get('protected_members', 0)}", table_cell_style), Paragraph("Private and protected attributes/methods", table_cell_style)],
                    [Paragraph("Public Members", table_cell_bold), Paragraph(str(m.get("public_members", 0)), table_cell_style), Paragraph("Publicly exposed attributes/methods", table_cell_style)],
                    [Paragraph("Lines of Code Analysed", table_cell_bold), Paragraph(f"{m.get('total_lines', 0):,}", table_cell_style), Paragraph("Total Lines of Code (LoC) inspected", table_cell_style)],
                    [Paragraph("Global Functions", table_cell_bold), Paragraph(str(m.get("total_functions", 0)), table_cell_style), Paragraph("Module/global-level procedural subroutines", table_cell_style)],
                ]
                
                metric_table = Table(m_data, colWidths=[2.2*inch, 1.5*inch, 3.5*inch])
                metric_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), c_primary),
                    ('PADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 1, c_border),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_neutral_light]),
                ]))
                repo_story.append(metric_table)
                repo_story.append(Spacer(1, 10))
                
        repo_story.append(Spacer(1, 15))
        story.append(KeepTogether(repo_story))

    # Build document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
