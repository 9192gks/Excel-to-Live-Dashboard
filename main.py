from pathlib import Path
from datetime import datetime

import pandas as pd
from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.config import APP_NAME, EXCEL_FILE

app = FastAPI(
    title=f"{APP_NAME} API",
    version="2.0.0",
    description="Local Excel-to-dashboard automation API.",
)


@app.get("/")
def root():
    return {
        "application": APP_NAME,
        "version": "2.0.0",
        "status": "running",
        "dashboard": "/dashboard.html",
        "api": "/api/data",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "excel_file": str(EXCEL_FILE),
        "excel_exists": EXCEL_FILE.exists(),
    }


@app.get("/dashboard.html")
async def dashboard():
    dashboard_path = Path(__file__).parent / "dashboard.html"
    return FileResponse(dashboard_path)


def find_column(df: pd.DataFrame, possible_names):
    normalized = {str(c).strip().lower(): c for c in df.columns}

    for name in possible_names:
        if name.lower() in normalized:
            return normalized[name.lower()]

    for col in df.columns:
        col_lower = str(col).strip().lower()
        for name in possible_names:
            if name.lower() in col_lower:
                return col

    raise KeyError(f"Could not find column. Expected one of: {possible_names}")


def build_dashboard_data():
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Excel source not found: {EXCEL_FILE}. "
            "Set EXCEL_FILE in .env to your workbook."
        )

    df = pd.read_excel(EXCEL_FILE, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]

    date_col = find_column(df, ["Date", "Order Date"])
    segment_col = find_column(df, ["Segment"])
    product_col = find_column(df, ["Product"])
    country_col = find_column(df, ["Country"])
    discount_col = find_column(df, ["Discount Band"])
    sales_col = find_column(df, ["Sales"])
    profit_col = find_column(df, ["Profit"])
    units_col = find_column(df, ["Units Sold", "Units"])

    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).copy()

    for col in [sales_col, profit_col, units_col]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["_year"] = df[date_col].dt.year
    df["_month"] = df[date_col].dt.month

    # Monthly: [year, month, sales, profit, units]
    monthly_group = (
        df.groupby(["_year", "_month"], as_index=False)[
            [sales_col, profit_col, units_col]
        ].sum()
    )

    monthly = [
        [
            int(row["_year"]),
            int(row["_month"]),
            float(row[sales_col]),
            float(row[profit_col]),
            float(row[units_col]),
        ]
        for _, row in monthly_group.iterrows()
    ]
    monthly.sort(key=lambda x: (x[0], x[1]))

    def make_group(column):
        grouped = (
            df.groupby(column, dropna=False)[
                [sales_col, profit_col, units_col]
            ]
            .sum()
            .reset_index()
        )

        result = []
        for _, row in grouped.iterrows():
            name = "Blank" if pd.isna(row[column]) else str(row[column])
            result.append(
                [
                    name,
                    float(row[sales_col]),
                    float(row[profit_col]),
                    float(row[units_col]),
                ]
            )

        result.sort(key=lambda x: x[1], reverse=True)
        return result

    segment = make_group(segment_col)
    product = make_group(product_col)
    country = make_group(country_col)
    discount = make_group(discount_col)

    years = sorted({int(x[0]) for x in monthly})
    years_display = ["All"] + [str(y) for y in years]

    # Comparable YoY for the latest two years over common months.
    yoy_sales = yoy_profit = yoy_units = "—"
    margin_change = "—"

    if len(years) >= 2:
        y1, y0 = years[-1], years[-2]
        common = sorted(
            set(df.loc[df["_year"] == y1, "_month"])
            & set(df.loc[df["_year"] == y0, "_month"])
        )

        a = df[df["_year"].eq(y1) & df["_month"].isin(common)]
        b = df[df["_year"].eq(y0) & df["_month"].isin(common)]

        s1, s0 = a[sales_col].sum(), b[sales_col].sum()
        p1, p0 = a[profit_col].sum(), b[profit_col].sum()
        u1, u0 = a[units_col].sum(), b[units_col].sum()

        yoy_sales = f"{(s1 / s0 - 1) * 100:.1f}%" if s0 else "—"
        yoy_profit = f"{(p1 / p0 - 1) * 100:.1f}%" if p0 else "—"
        yoy_units = f"{(u1 / u0 - 1) * 100:.1f}%" if u0 else "—"
        margin_change = (
            f"{((p1 / s1) - (p0 / s0)) * 100:.1f} pt"
            if s1 and s0
            else "—"
        )

    total_sales = float(df[sales_col].sum())
    total_profit = float(df[profit_col].sum())
    total_units = float(df[units_col].sum())
    margin = total_profit / total_sales if total_sales else 0

    insights = []

    if len(segment) >= 1:
        top2 = segment[:2]
        top2_sales = sum(x[1] for x in top2)
        insights.append(
            [
                "",
                f"<b>Top sales segments.</b> "
                f"{top2[0][0]} and "
                f"{top2[1][0] if len(top2) > 1 else 'the next segment'} "
                f"together contribute {top2_sales / 1e6:.1f}M in sales.",
            ]
        )

        loss = [x for x in segment if x[2] < 0]
        if loss:
            x = loss[0]
            margin_loss = x[2] / x[1] * 100 if x[1] else 0
            insights.append(
                [
                    "w",
                    f"<b>{x[0]} is loss-making.</b> "
                    f"It generated {x[1] / 1e6:.1f}M in sales but "
                    f"{x[2] / 1e6:.1f}M profit ({margin_loss:.1f}% margin).",
                ]
            )

    if discount:
        high = next(
            (x for x in discount if str(x[0]).lower() == "high"), None
        )
        none = next(
            (
                x
                for x in discount
                if str(x[0]).lower() in ("none", "no discount")
            ),
            None,
        )
        if high and none and high[1] and none[1]:
            insights.append(
                [
                    "w",
                    f"<b>Discounts are affecting margin.</b> "
                    f"No-discount margin is {none[2] / none[1] * 100:.1f}% "
                    f"versus {high[2] / high[1] * 100:.1f}% for high discount.",
                ]
            )

    if country:
        worst = min(
            country,
            key=lambda x: x[2] / x[1] if x[1] else 999,
        )
        worst_margin = worst[2] / worst[1] * 100 if worst[1] else 0
        insights.append(
            [
                "w",
                f"<b>{worst[0]} has the weakest margin</b> "
                f"at {worst_margin:.1f}% among the loaded countries.",
            ]
        )

    return {
        "monthly": monthly,
        "segment": segment,
        "product": product,
        "country": country,
        "discount": discount,
        "years": years_display,
        "yoy_sales": yoy_sales,
        "yoy_profit": yoy_profit,
        "yoy_units": yoy_units,
        "margin_change": margin_change,
        "total_sales": total_sales,
        "total_profit": total_profit,
        "total_units": total_units,
        "margin": margin,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file": str(EXCEL_FILE),
        "insights": insights,
    }


@app.get("/api/data")
async def dashboard_data():
    try:
        return build_dashboard_data()
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc)},
        )
