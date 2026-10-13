
"""Create a clean, user-facing Excel workbook with Company Insights and PIT Disclosures."""

from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from config import OUTPUT_DIR, EXCEL_FILENAME

MAIN_COLUMNS = [
    "Disclosure Date", "Company", "Symbol", "Person", "Category", "Action",
    "Shares", "Price Per Share", "Transaction Value", "Transaction Date",
    "Mode", "Exchange", "Shares Before", "Holding % Before",
    "Shares After", "Holding % After", "Submission", "Revision Reason",
]


def _is_open_market(mode: str | None) -> bool:
    if not mode:
        return False
    m = str(mode).lower()
    return any(term in m for term in ("market", "block"))


def _is_promoter(category: str | None) -> bool:
    if not category:
        return False
    c = str(category).lower()
    return "promoter" in c or "director" in c


def build_company_insights(rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Summarize and rate insider trading disclosures company-wise."""
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    df["Value_Num"] = pd.to_numeric(df["Transaction Value"], errors="coerce").fillna(0)
    df["Action_Clean"] = df["Action"].fillna("").astype(str).str.strip().str.title()
    df["Mode_Clean"] = df["Mode"].fillna("").astype(str).str.strip()

    records = []
    for symbol, group in df.groupby("Symbol"):
        company = group["Company"].iloc[0] or symbol
        total_trades = len(group)
        unique_insiders = group["Person"].dropna().nunique()

        # Open market buy / sell
        om_buy_df = group[(group["Action_Clean"] == "Buy") & group["Mode_Clean"].apply(_is_open_market)]
        om_sell_df = group[(group["Action_Clean"] == "Sell") & group["Mode_Clean"].apply(_is_open_market)]

        om_buy_val = om_buy_df["Value_Num"].sum()
        om_sell_val = om_sell_df["Value_Num"].sum()
        net_om_val = om_buy_val - om_sell_val

        # Promoter buyers / sellers in open market
        prom_buyers = group[
            (group["Action_Clean"] == "Buy")
            & group["Category"].apply(_is_promoter)
            & group["Mode_Clean"].apply(_is_open_market)
        ]["Person"].nunique()

        prom_sellers = group[
            (group["Action_Clean"] == "Sell")
            & group["Category"].apply(_is_promoter)
            & group["Mode_Clean"].apply(_is_open_market)
        ]["Person"].nunique()

        # Non-market / ESOP transactions
        esop_val = group[group["Mode_Clean"].str.upper().str.contains("ESOP|ESOS", na=False)]["Value_Num"].sum()
        pledge_create = len(
            group[
                group["Action_Clean"].str.contains("Pledge", na=False)
                & ~group["Action_Clean"].str.contains("Revoke", na=False)
            ]
        )

        # Rating Score calculation (0 to 100)
        score = 50.0
        if net_om_val > 0:
            score += 15.0 + min(25.0, (net_om_val / 1e7) * 5.0)
        elif net_om_val < 0:
            score -= 15.0 + min(25.0, (abs(net_om_val) / 1e7) * 5.0)

        score += min(20.0, prom_buyers * 10.0)
        score -= min(20.0, prom_sellers * 10.0)

        if prom_buyers >= 2 or (unique_insiders >= 3 and net_om_val > 0):
            score += 10.0

        if pledge_create > 0 and net_om_val <= 0:
            score -= 10.0

        final_score = int(max(0, min(100, round(score))))

        if final_score >= 80:
            rating, signal = "5/5 Stars (★★★★★)", "Strong Bullish"
        elif final_score >= 65:
            rating, signal = "4/5 Stars (★★★★☆)", "Bullish"
        elif final_score >= 45:
            rating, signal = "3/5 Stars (★★★☆☆)", "Neutral"
        elif final_score >= 30:
            rating, signal = "2/5 Stars (★★☆☆☆)", "Caution"
        else:
            rating, signal = "1/5 Star (★☆☆☆☆)", "Bearish"

        # Insight sentence
        net_cr = net_om_val / 1e7
        if prom_buyers > 0 and net_om_val > 0:
            insight = f"🚀 {prom_buyers} Promoter(s) bought ₹{net_cr:.2f} Cr in Open Market."
        elif net_om_val > 0:
            insight = f"🟢 Net Insider buying of ₹{net_cr:.2f} Cr across {unique_insiders} insider(s)."
        elif prom_sellers > 0 and net_om_val < 0:
            insight = f"🔴 {prom_sellers} Promoter(s) sold ₹{abs(net_cr):.2f} Cr in Open Market."
        elif net_om_val < 0:
            insight = f"⚠️ Net Insider selling of ₹{abs(net_cr):.2f} Cr."
        elif esop_val > 0:
            insight = f"📦 ESOP exercises totaling ₹{esop_val / 1e7:.2f} Cr."
        elif pledge_create > 0:
            insight = "🔒 Promoter pledge creation recorded."
        else:
            insight = "ℹ️ Inter-se / Non-market transactions recorded."

        records.append({
            "Symbol": symbol,
            "Company": company,
            "Conviction Score": final_score,
            "Rating": rating,
            "Signal": signal,
            "Net Open Market Buy (₹ Cr)": round(net_cr, 2),
            "Open Market Buy (₹ Cr)": round(om_buy_val / 1e7, 2),
            "Open Market Sell (₹ Cr)": round(om_sell_val / 1e7, 2),
            "Promoter Buyers": prom_buyers,
            "Promoter Sellers": prom_sellers,
            "Total Trades": total_trades,
            "Unique Insiders": unique_insiders,
            "ESOP Value (₹ Cr)": round(esop_val / 1e7, 2),
            "Key Insight": insight,
        })

    insights_df = pd.DataFrame(records)
    # Sort by Conviction Score desc, then Net Open Market Buy desc
    insights_df.sort_values(
        by=["Conviction Score", "Net Open Market Buy (₹ Cr)"],
        ascending=[False, False],
        inplace=True,
    )

    insights_df.insert(0, "Rank", range(1, len(insights_df) + 1))
    return insights_df


def export(rows: list[dict[str, Any]]) -> Path:
    """Export disclosures to Excel with Company Insights as Sheet 1."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean up old CSV if present
    csv_file = OUTPUT_DIR / "NSE_PIT_Disclosures.csv"
    if csv_file.exists():
        try:
            csv_file.unlink()
        except Exception:
            pass

    main_df = pd.DataFrame(rows)
    for col in MAIN_COLUMNS:
        if col not in main_df.columns:
            main_df[col] = None
    main_df = main_df[MAIN_COLUMNS]

    insights_df = build_company_insights(rows)

    excel_path = OUTPUT_DIR / EXCEL_FILENAME

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        insights_df.to_excel(writer, sheet_name="Company Insights", index=False)
        main_df.to_excel(writer, sheet_name="PIT Disclosures", index=False)

    _format_workbook(excel_path)
    return excel_path


def _format_workbook(path: Path) -> None:
    wb = load_workbook(path)

    for ws in wb.worksheets:
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        ws.row_dimensions[1].height = 28

        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
            cell.alignment = Alignment(horizontal="center", vertical="center")

        thin = Side(style="thin", color="D9E1F2")
        for row in ws.iter_rows():
            for cell in row:
                cell.border = Border(bottom=thin)
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        widths = {}
        for row in ws.iter_rows():
            for cell in row:
                widths[cell.column] = max(widths.get(cell.column, 0), len(str(cell.value or "")) + 2)

        for col_idx, width in widths.items():
            ws.column_dimensions[get_column_letter(col_idx)].width = min(max(width, 12), 48)

    # -------------------------------------------------------------
    # Formatting Sheet 1: Company Insights
    # -------------------------------------------------------------
    ws_ins = wb["Company Insights"]
    header_ins = {cell.value: cell.column for cell in ws_ins[1]}

    # Colors for Signal / Rating cells
    signal_styles = {
        "Strong Bullish": (PatternFill("solid", fgColor="E2EFDA"), Font(color="375623", bold=True)),
        "Bullish": (PatternFill("solid", fgColor="F2FCE4"), Font(color="375623", bold=True)),
        "Neutral": (PatternFill("solid", fgColor="F2F2F2"), Font(color="333333")),
        "Caution": (PatternFill("solid", fgColor="FFF2CC"), Font(color="7F6000", bold=True)),
        "Bearish": (PatternFill("solid", fgColor="FCE4D6"), Font(color="C65911", bold=True)),
    }

    for row in range(2, ws_ins.max_row + 1):
        for col_name in (
            "Net Open Market Buy (₹ Cr)",
            "Open Market Buy (₹ Cr)",
            "Open Market Sell (₹ Cr)",
            "ESOP Value (₹ Cr)",
        ):
            if col_name in header_ins:
                ws_ins.cell(row, header_ins[col_name]).number_format = '₹#,##0.00;[Red]-₹#,##0.00;"-"'

        for col_name in ("Rank", "Conviction Score", "Promoter Buyers", "Promoter Sellers", "Total Trades", "Unique Insiders"):
            if col_name in header_ins:
                ws_ins.cell(row, header_ins[col_name]).number_format = '#,##0'

        if "Signal" in header_ins:
            cell = ws_ins.cell(row, header_ins["Signal"])
            sig_val = str(cell.value or "")
            if sig_val in signal_styles:
                fill, font = signal_styles[sig_val]
                cell.fill = fill
                cell.font = font

        if "Rating" in header_ins:
            cell = ws_ins.cell(row, header_ins["Rating"])
            cell.alignment = Alignment(horizontal="center", vertical="top")

    if ws_ins.max_row >= 2:
        ref_ins = f"A1:{get_column_letter(ws_ins.max_column)}{ws_ins.max_row}"
        tab_ins = Table(displayName="CompanyInsightsTable", ref=ref_ins)
        tab_ins.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium9",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws_ins.add_table(tab_ins)

    # -------------------------------------------------------------
    # Formatting Sheet 2: PIT Disclosures
    # -------------------------------------------------------------
    ws_disc = wb["PIT Disclosures"]
    header_disc = {cell.value: cell.column for cell in ws_disc[1]}
    for row in range(2, ws_disc.max_row + 1):
        for name in ("Shares", "Shares Before", "Shares After"):
            if name in header_disc:
                ws_disc.cell(row, header_disc[name]).number_format = '#,##0'
        if "Price Per Share" in header_disc:
            ws_disc.cell(row, header_disc["Price Per Share"]).number_format = '₹#,##0.00'
        if "Transaction Value" in header_disc:
            ws_disc.cell(row, header_disc["Transaction Value"]).number_format = '₹#,##0.00'
        for name in ("Holding % Before", "Holding % After"):
            if name in header_disc:
                ws_disc.cell(row, header_disc[name]).number_format = '0.00%'

    if ws_disc.max_row >= 2:
        ref_disc = f"A1:{get_column_letter(ws_disc.max_column)}{ws_disc.max_row}"
        tab_disc = Table(displayName="PITDisclosuresTable", ref=ref_disc)
        tab_disc.tableStyleInfo = TableStyleInfo(
            name="TableStyleMedium2",
            showFirstColumn=False,
            showLastColumn=False,
            showRowStripes=True,
            showColumnStripes=False,
        )
        ws_disc.add_table(tab_disc)

    wb.save(path)

