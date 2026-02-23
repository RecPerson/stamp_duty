# app.py
import streamlit as st

# =========================================
# Money-safe helpers
# =========================================
def round_up_to(value: float, step_dollars: int) -> float:
    """
    Round value UP to the next multiple of `step_dollars` using integer cents
    to avoid floating-point precision issues.
    Example: round_up_to(110000.00, 100) -> 110000.00  (NOT 110100.00)
    """
    step_cents = step_dollars * 100
    value_cents = int(round(value * 100))  # normalize to exact cents
    rounded_cents = ((value_cents + step_cents - 1) // step_cents) * step_cents
    return rounded_cents / 100.0


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


def fmt_pct(x: float) -> str:
    return f"{x:.2%}"


# =========================================
# GST helpers
# =========================================
def gst_is_inclusive(mode: str) -> bool:
    return mode == "GST inclusive"


def to_inclusive(amount: float, mode: str) -> float:
    return amount if gst_is_inclusive(mode) else amount * 1.10


def to_exclusive(amount: float, mode: str) -> float:
    return amount if not gst_is_inclusive(mode) else amount / 1.10


# =========================================
# Core calculation with full breakdown
# =========================================
def calculate_all(
    state: str,
    price_entered: float,
    costs_entered: float,
    discount_entered: float,
    null_gst: float,
    gst_mode: str,
    lct_choice: str,                # "Fuel Efficient" | "Not Fuel Efficient" | "Exempt"
    qld_base: str = "New/Used",     # "New/Used" | "GVM"
    qld_cyl: str = "electric/hybrid",  # "electric/hybrid" | "1-4 cylinders" | "5-6 cylinders" | "7+ cylinders"
    tas_vehicle_type: str = "passenger (< 9 people and not utes, motor cycles, panel vans)",
    vic_category: str = "Private (passenger)"
):
    lines = []
    lines.append("=== Inputs & GST Mode ===")
    lines.append(f"GST Mode: {gst_mode}")
    lines.append(f"Price entered: {fmt_money(price_entered)}")
    lines.append(f"Other GSTable costs: {fmt_money(costs_entered)}")
    lines.append(f"Discount entered: {fmt_money(discount_entered)}")
    lines.append(f"CTP/rego (no GST): {fmt_money(null_gst)}")
    lines.append("")

    # Normalize to GST-inclusive for invoice totals and LCT thresholds
    price_incl = to_inclusive(price_entered, gst_mode)
    costs_incl = to_inclusive(costs_entered, gst_mode)
    discount_incl = to_inclusive(discount_entered, gst_mode)

    lines.append("=== GST-normalized values (for invoice/LCT thresholds) ===")
    lines.append(f"Price (incl GST): {fmt_money(price_incl)}")
    lines.append(f"Costs (incl GST): {fmt_money(costs_incl)}")
    lines.append(f"Discount (incl GST): {fmt_money(discount_incl)}")
    lines.append("")

    # --- LCT (Luxury Car Tax) ---
    lct_base = price_incl + costs_incl
    LCT_FUEL_EFFICIENT_THRESHOLD = 91_387.0
    LCT_NON_EFFICIENT_THRESHOLD  = 80_567.0
    LCT_RATE = 0.33
    LCT_amount = 0.0

    lines.append("=== LCT Calculation ===")
    lines.append(f"LCT category: {lct_choice}")
    lines.append(f"LCT base (price + costs, incl GST): {fmt_money(lct_base)}")
    if lct_choice == "Fuel Efficient":
        thr = LCT_FUEL_EFFICIENT_THRESHOLD
        lines.append(f"Threshold (fuel efficient): {fmt_money(thr)}")
        if lct_base > thr:
            taxable = lct_base - thr
            lines.append(f"Amount above threshold: {fmt_money(taxable)}")
            lines.append(f"LCT rate: {fmt_pct(LCT_RATE)}")
            lines.append("LCT amount is multiplied by 10/11 to remove the GST component.")
            LCT_amount = taxable * LCT_RATE * 10 / 11
            lines.append(f"LCT payable: {fmt_money(LCT_amount)}")
        else:
            lines.append("Below threshold: LCT = $0.00")
    elif lct_choice == "Not Fuel Efficient":
        thr = LCT_NON_EFFICIENT_THRESHOLD
        lines.append(f"Threshold (non-fuel efficient): {fmt_money(thr)}")
        if lct_base > thr:
            taxable = lct_base - thr
            lines.append(f"Amount above threshold: {fmt_money(taxable)}")
            lines.append(f"LCT rate: {fmt_pct(LCT_RATE)}")
            lines.append("LCT amount is multiplied by 10/11 to remove the GST component.")
            LCT_amount = taxable * LCT_RATE * 10 / 11
            lines.append(f"LCT payable: {fmt_money(LCT_amount)}")
        else:
            lines.append("Below threshold: LCT = $0.00")
    else:
        lines.append("Exempt: LCT = $0.00")
    lines.append("")

    # --- State stamp duty ---
    stamp_duty = 0.0
    rounded_dutiable = 0.0

    lines.append("=== Stamp Duty Calculation ===")
    lines.append(f"State: {state}")

    if state == "Queensland":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        over_100k = rounded_dutiable > 100_000
        lines.append(f"Base type: {qld_base}")
        lines.append(f"Vehicle type: {qld_cyl}")
        lines.append(f"Threshold > $100,000? {'Yes' if over_100k else 'No'}")

        if qld_base == "New/Used":
            if qld_cyl == "electric/hybrid":
                rate = 4.0 if over_100k else 2.0
            elif qld_cyl == "1-4 cylinders":
                rate = 5.0 if over_100k else 3.0
            elif qld_cyl == "5-6 cylinders":
                rate = 5.5 if over_100k else 3.5
            elif qld_cyl == "7+ cylinders":
                rate = 6.0 if over_100k else 4.0
            else:
                rate = 0.0
        elif qld_base == "GVM":
            if qld_cyl == "electric/hybrid":
                rate = 2.0
            elif qld_cyl == "1-4 cylinders":
                rate = 3.0
            elif qld_cyl == "5-6 cylinders":
                rate = 3.5
            elif qld_cyl == "7+ cylinders":
                rate = 4.0
            else:
                rate = 0.0
        else:
            rate = 0.0

        lines.append(f"Duty rate applied: {rate:.2f}%")
        stamp_duty = rounded_dutiable * rate / 100.0
        lines.append(f"Stamp duty = {fmt_money(rounded_dutiable)} × {rate:.2f}% = {fmt_money(stamp_duty)}")

    elif state == "Tasmania":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        vt = tas_vehicle_type
        lines.append(f"Vehicle type: {vt}")

        if vt.startswith("passenger"):
            if rounded_dutiable <= 600:
                stamp_duty = 20
                lines.append("Passenger ≤ $600: flat $20 duty.")
            elif rounded_dutiable <= 35_000:
                stamp_duty = rounded_dutiable * 0.03
                lines.append("Passenger $601–$35,000: 3% of dutiable value.")
            elif rounded_dutiable <= 40_000:
                stamp_duty = 1_050 + ((rounded_dutiable - 35_000) * 0.11)
                lines.append("Passenger $35,001–$40,000: $1,050 + 11% of amount over $35,000.")
            else:
                stamp_duty = rounded_dutiable * 0.04
                lines.append("Passenger > $40,000: 4% of dutiable value.")
        elif vt.startswith("commercial up to 4.5t"):
            stamp_duty = rounded_dutiable * 0.03
            lines.append("Commercial ≤ 4.5t: 3% of dutiable value.")
        elif vt.startswith("commercial more than 4.5t"):
            stamp_duty = rounded_dutiable * 0.01
            lines.append("Commercial > 4.5t: 1% of dutiable value.")
        elif vt.startswith("manufacturer fleet"):
            stamp_duty = rounded_dutiable * 0.035
            lines.append("Manufacturer fleet: 3.5% of dutiable value.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    elif state == "New South Wales":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        if rounded_dutiable <= 44_900:
            stamp_duty = rounded_dutiable * 0.03
            lines.append("NSW tier ≤ $44,900: 3% of dutiable value.")
        else:
            stamp_duty = 1_350 + (rounded_dutiable - 45_000) * 0.05
            lines.append("NSW tier > $44,900: $1,350 + 5% of amount over $45,000.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    elif state == "Victoria":
        # VIC build-up: EX-GST -> apply GST once -> add LCT -> round UP to $200
        price_ex = to_exclusive(price_entered, gst_mode)
        discount_ex = to_exclusive(discount_entered, gst_mode)
        vic_dutiable_ex = max(price_ex - discount_ex, 0.0)
        vic_dutiable_incl = vic_dutiable_ex * 1.10
        vic_plus_lct = vic_dutiable_incl + LCT_amount

        lines.append("VIC build-up:")
        lines.append(f"  EX-GST base (price - discount): {fmt_money(vic_dutiable_ex)}")
        lines.append(f"  Add GST once (×1.10): {fmt_money(vic_dutiable_incl)}")
        lines.append(f"  Add LCT: {fmt_money(LCT_amount)} → {fmt_money(vic_plus_lct)} before rounding")

        rounded_dutiable = round_up_to(vic_plus_lct, 200)
        lines.append(f"  Round up to next $200: {fmt_money(rounded_dutiable)}")

        def vic_passenger_rate(value: float) -> float:
            if value <= 80_567:
                return 0.042
            elif value <= 100_000:
                return 0.052
            elif value <= 150_000:
                return 0.070
            else:
                return 0.090

        lines.append(f"Category: {vic_category}")
        if vic_category == "Private (passenger)":
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Passenger tiered rate applied: {fmt_pct(rate)}")
        elif vic_category == "Low emission (passenger)":
            rate = 0.042
            lines.append("Low emission passenger: 4.2%")
        elif vic_category == "Primary producer (passenger)":
            rate = 0.042
            lines.append("Primary producer passenger: 4.2%")
        elif vic_category == "Commercial (new registration)":
            rate = 0.027
            lines.append("Commercial (new): 2.7%")
        elif vic_category == "Commercial (used/transfer)":
            rate = 0.042
            lines.append("Commercial (used/transfer): 4.2%")
        elif vic_category == "Demonstrator (passenger)":
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Demonstrator passenger (tiered): {fmt_pct(rate)}")
        elif vic_category == "Demo commercial (used/transfer)":
            rate = 0.042
            lines.append("Demo commercial (used/transfer): 4.2%")
        else:
            rate = vic_passenger_rate(rounded_dutiable)
            lines.append(f"Default passenger tiered rate: {fmt_pct(rate)}")

        stamp_duty = rounded_dutiable * rate
        lines.append(f"Stamp duty = {fmt_money(rounded_dutiable)} × {fmt_pct(rate)} = {fmt_money(stamp_duty)}")

    elif state == "South Australia":
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")

        if rounded_dutiable <= 45_000:
            stamp_duty = rounded_dutiable * 0.03
            lines.append("SA tier ≤ $45,000: 3% of dutiable value.")
        elif rounded_dutiable <= 60_000:
            stamp_duty = 1_350 + (rounded_dutiable - 45_000) * 0.04
            lines.append("SA $45,001–$60,000: $1,350 + 4% of amount over $45,000.")
        else:
            stamp_duty = 1,950 + (rounded_dutiable - 60_000) * 0.05  # corrected below (string shows how; real calc next line)
            stamp_duty = 1950 + (rounded_dutiable - 60_000) * 0.05
            lines.append("SA > $60,000: $1,950 + 5% of amount over $60,000.")
        lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")

    else:
        dutiable_before_round = max(price_incl - discount_incl, 0.0) + LCT_amount
        lines.append(f"Dutiable value before rounding (price - discount + LCT): {fmt_money(dutiable_before_round)}")
        rounded_dutiable = round_up_to(dutiable_before_round, 100)
        lines.append(f"Rounded to next $100: {fmt_money(rounded_dutiable)}")
        lines.append("No duty calculation implemented for this state.")
        stamp_duty = 0.0

    lines.append("")
    lines.append("=== Invoice Totals ===")
    GST_component = (price_incl + costs_incl - discount_incl) / 11.0
    total = price_incl + costs_incl + stamp_duty + null_gst - discount_incl + LCT_amount
    lines.append(f"GST component (1/11 of GSTable items): {fmt_money(GST_component)}")
    lines.append(f"Rounded dutiable value used: {fmt_money(rounded_dutiable)}")
    lines.append(f"Stamp duty: {fmt_money(stamp_duty)}")
    lines.append(f"LCT: {fmt_money(LCT_amount)}")
    lines.append(f"Total purchase price: {fmt_money(total)}")

    breakdown = "\n".join(lines)

    return {
        "rounded_dutiable": rounded_dutiable,
        "stamp_duty": stamp_duty,
        "GST": GST_component,
        "LCT": LCT_amount,
        "total": total,
        "breakdown": breakdown,
    }


# =========================================
# Streamlit UI
# =========================================
st.set_page_config(page_title="Stamp Duty Calculator (Streamlit)", layout="wide")
st.title("Stamp Duty Calculator")
st.caption("Fixed cents‑safe rounding • Full LCT + stamp duty breakdown")

with st.form("calc_form", border=True):
    col1, col2, col3 = st.columns([1.2, 1.2, 1.1])

    with col1:
        state = st.selectbox(
            "State",
            ["Queensland", "New South Wales", "South Australia", "Northern Territory", "Tasmania", "Victoria"],
            index=0,
        )
        gst_mode = st.selectbox("Amounts entered are", ["GST inclusive", "GST exclusive"], index=0)
        price_entered = st.number_input("Price (dutiable items)", min_value=0.0, step=100.0, value=0.0, format="%.2f")
        costs_entered = st.number_input("Other costs (GSTable)", min_value=0.0, step=50.0, value=0.0, format="%.2f")

    with col2:
        discount_entered = st.number_input("Discount", min_value=0.0, step=50.0, value=0.0, format="%.2f")
        null_gst = st.number_input("CTP/rego (no GST)", min_value=0.0, step=10.0, value=0.0, format="%.2f")
        lct_choice = st.selectbox("LCT Category", ["Fuel Efficient", "Not Fuel Efficient", "Exempt"], index=2)

        # QLD-specific inputs
        qld_base = "New/Used"
        qld_cyl = "electric/hybrid"
        if state == "Queensland":
            st.subheader("Queensland options", anchor=False)
            qld_base = st.selectbox("Base Type (Qld)", ["New/Used", "GVM"], index=0)
            qld_cyl = st.selectbox("Vehicle Type (Qld)", ["electric/hybrid", "1-4 cylinders", "5-6 cylinders", "7+ cylinders"], index=0)

    with col3:
        tas_vehicle_type = "passenger (< 9 people and not utes, motor cycles, panel vans)"
        vic_category = "Private (passenger)"

        if state == "Tasmania":
            st.subheader("Tasmania options", anchor=False)
            tas_vehicle_type = st.selectbox(
                "Vehicle Type (Tas)",
                [
                    "passenger (< 9 people and not utes, motor cycles, panel vans)",
                    "commercial up to 4.5t",
                    "commercial more than 4.5t",
                    "manufacturer fleet discount (except heavy vehicles)",
                ],
                index=0,
            )

        if state == "Victoria":
            st.subheader("Victoria options", anchor=False)
            vic_category = st.selectbox(
                "Category (Vic)",
                [
                    "Private (passenger)",
                    "Low emission (passenger)",
                    "Primary producer (passenger)",
                    "Commercial (new registration)",
                    "Commercial (used/transfer)",
                    "Demonstrator (passenger)",
                    "Demo commercial (used/transfer)",
                ],
                index=0,
            )

    submitted = st.form_submit_button("Calculate", type="primary")

if submitted:
    res = calculate_all(
        state=state,
        price_entered=price_entered,
        costs_entered=costs_entered,
        discount_entered=discount_entered,
        null_gst=null_gst,
        gst_mode=gst_mode,
        lct_choice=lct_choice,
        qld_base=qld_base,
        qld_cyl=qld_cyl,
        tas_vehicle_type=tas_vehicle_type,
        vic_category=vic_category,
    )

    # Summaries
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Rounded Dutiable Value", fmt_money(res["rounded_dutiable"]))
    c2.metric("Stamp Duty", fmt_money(res["stamp_duty"]))
    c3.metric("GST Component", fmt_money(res["GST"]))
    c4.metric("LCT", fmt_money(res["LCT"]))
    c5.metric("Total Purchase Price", fmt_money(res["total"]))

    # Detailed breakdown
    with st.expander("Detailed Calculation Breakdown", expanded=True):
        st.code(res["breakdown"], language="text")

else:
    st.info("Enter your values and click **Calculate**. The detailed breakdown will show exactly how LCT and stamp duty are computed for the selected state.")
