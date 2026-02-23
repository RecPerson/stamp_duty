# app.py
import streamlit as st
import math

# =========================
# Page config
# =========================
st.set_page_config(
    page_title="Tony White Internal Audit Sales Deals Calculator",
    page_icon="🧮",
    layout="centered",
)

st.title("Tony White Internal Audit Sales Deals Calculator")
st.caption("Web version (Streamlit) converted from your Tkinter app")

# =========================
# Utility + GST helpers
# =========================
def round_up_to(value: float, step: int) -> int:
    """Round value UP to the next multiple of `step`."""
    if step <= 0:
        return int(value)
    return int(math.ceil(value / step) * step)

def rounded_dutiable_100(price_incl: float, discount_incl: float) -> int:
    """Generic dutiable value: (price - discount), rounded up to next $100."""
    base = max(price_incl - discount_incl, 0.0)
    return round_up_to(base, 100)

def to_inclusive(amount: float, gst_mode: str) -> float:
    return amount if gst_mode == "GST inclusive" else amount * 1.10

def to_exclusive(amount: float, gst_mode: str) -> float:
    return amount if gst_mode == "GST exclusive" else amount / 1.10

def mode_suffix(gst_mode: str) -> str:
    return "(incl GST)" if gst_mode == "GST inclusive" else "(excl GST)"

# =========================
# Core calculation
# =========================
def calculate(
    state: str,
    category: str,
    gst_mode: str,
    price_entered: float,
    costs_entered: float,
    null_gst: float,
    discount_entered: float,
    qld_cyl: str,
    qld_base: str,
    tas_vehicle_type: str,
    vic_category: str,
    lct_selection: str,
):
    # Normalize to GST-inclusive for totals and most dutiable base uses
    price    = to_inclusive(price_entered, gst_mode)
    costs    = to_inclusive(costs_entered, gst_mode)
    discount = to_inclusive(discount_entered, gst_mode)

    is_motorcycle = (category == "Motorcycle")
    stamp_duty = 0.0

    # ---- LCT (GST-inclusive base), cars only (not motorcycles) ----
    LCT_amount = 0.0
    if not is_motorcycle:
        lct_base = price + costs - discount
        LCT_FUEL_EFFICIENT_THRESHOLD = 91_387.0
        LCT_NON_EFFICIENT_THRESHOLD  = 80_567.0
        LCT_rate = 0.33

        if lct_selection == "Fuel Efficient":
            if lct_base > LCT_FUEL_EFFICIENT_THRESHOLD:
                LCT_amount = (lct_base - LCT_FUEL_EFFICIENT_THRESHOLD) * LCT_rate * 10 / 11
        elif lct_selection == "Not Fuel Efficient":
            if lct_base > LCT_NON_EFFICIENT_THRESHOLD:
                LCT_amount = (lct_base - LCT_NON_EFFICIENT_THRESHOLD) * LCT_rate * 10 / 11
        # "Exempt" => LCT_amount stays 0

    # Default rounded value; may be recomputed in state blocks
    rounded_price = rounded_dutiable_100(price, discount)

    # ---- State-specific duty ----
    if state == "Queensland":
        if is_motorcycle:
