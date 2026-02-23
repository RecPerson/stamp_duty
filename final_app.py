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
            # QLD Motorcycle: flat 2% on rounded(price - discount)
            stamp_duty = rounded_price * 0.02
        else:
            over_100k = (price - discount) > 100_000
            cyl_choice = qld_cyl
            base_choice = qld_base

            if base_choice == "New/Used":
                if cyl_choice == "electric/hybrid":
                    rate = 4.0 if over_100k else 2.0
                elif cyl_choice == "1-4 cylinders":
                    rate = 5.0 if over_100k else 3.0
                elif cyl_choice == "5-6 cylinders":
                    rate = 5.5 if over_100k else 3.5
                elif cyl_choice == "7+ cylinders":
                    rate = 6.0 if over_100k else 4.0
                else:
                    rate = 3.0
            elif base_choice == "GVM":
                if cyl_choice == "electric/hybrid":
                    rate = 2.0
                elif cyl_choice == "1-4 cylinders":
                    rate = 3.0
                elif cyl_choice == "5-6 cylinders":
                    rate = 3.5
                elif cyl_choice == "7+ cylinders":
                    rate = 4.0
                else:
                    rate = 3.0
            else:
                rate = 3.0

            stamp_duty = rounded_price * rate / 100.0

    elif state == "Tasmania":
        if is_motorcycle:
            # TAS Motorcycle: flat 3%
            rounded_price = rounded_dutiable_100(price, discount)
            stamp_duty = rounded_price * 0.03
        else:
            vt_choice = tas_vehicle_type
            rounded_price = rounded_dutiable_100(price, discount)
            if vt_choice.startswith("passenger"):
                if rounded_price <= 600:
                    stamp_duty = 20
                elif rounded_price <= 35_000:
                    stamp_duty = rounded_price * 3 / 100
                elif rounded_price <= 40_000:
                    stamp_duty = 1050 + ((rounded_price - 35_000) * 11 / 100)
                else:
                    stamp_duty = rounded_price * 4 / 100
            elif vt_choice.startswith("commercial up to 4.5t"):
                stamp_duty = rounded_price * 3 / 100
            elif vt_choice.startswith("commercial more than 4.5t"):
                stamp_duty = rounded_price * 1 / 100
            elif vt_choice.startswith("manufacturer fleet"):
                stamp_duty = rounded_price * 3.5 / 100

    elif state == "New South Wales":
        if is_motorcycle:
            rounded_price = rounded_dutiable_100(price, discount)
            stamp_duty = rounded_price * 0.03
        else:
            # NSW includes LCT in the dutiable base; always deduct discount
            nsw_dutiable = max((price - discount) + LCT_amount, 0.0)
            rounded_price = round_up_to(nsw_dutiable, 100)
            if rounded_price <= 44_900:
                stamp_duty = rounded_price * 0.03
            else:
                stamp_duty = 1350 + (rounded_price - 45_000) * 0.05

    elif state == "Victoria":
        # VIC special build-up (use EX-GST for price/discount -> add GST once -> round to $200)
        price_ex = to_exclusive(price_entered, gst_mode)
        discount_ex = to_exclusive(discount_entered, gst_mode)

        vic_dutiable_ex   = max(price_ex - discount_ex, 0.0)
        vic_dutiable_incl = vic_dutiable_ex * 1.10
        vic_rounded       = round_up_to(vic_dutiable_incl, 200)

        if is_motorcycle:
            if vic_category == "Motorcycle (new registration)":
                rate = 0.027  # $5.40 per $200
            else:  # "Motorcycle (used/transfer)"
                rate = 0.042  # $8.40 per $200
        else:
            def passenger_rate_for(value: float) -> float:
                if value <= 80_567:
                    return 0.042
                elif value <= 100_000:
                    return 0.052
                elif value <= 150_000:
                    return 0.070
                else:
                    return 0.090

            if vic_category == "Private (passenger)":
                rate = passenger_rate_for(vic_rounded)
            elif vic_category == "Low emission (passenger)":
                rate = 0.042
            elif vic_category == "Primary producer (passenger)":
                rate = 0.042
            elif vic_category == "Commercial (new registration)":
                rate = 0.027
            elif vic_category == "Commercial (used/transfer)":
                rate = 0.042
            elif vic_category == "Demonstrator (passenger)":
                rate = passenger_rate_for(vic_rounded)
            elif vic_category == "Demo commercial (used/transfer)":
                rate = 0.042
            else:
                rate = passenger_rate_for(vic_rounded)

        stamp_duty = vic_rounded * rate
        rounded_price = vic_rounded

    elif state == "South Australia":
        rounded_price = rounded_dutiable_100(price, discount)
        if is_motorcycle:
            stamp_duty = rounded_price * 0.03
        else:
            if rounded_price <= 45_000:
                stamp_duty = rounded_price * 0.03
            elif rounded_price <= 60_000:
                stamp_duty = 1_350 + (rounded_price - 45_000) * 0.04
            else:
                stamp_duty = 1_950 + (rounded_price - 60_000) * 0.05

    elif state == "Northern Territory":
        rounded_price = rounded_dutiable_100(price, discount)
        stamp_duty = rounded_price * 0.03

    # Totals
    GST = (price + costs - discount) / 11.0
    Total = price + costs + stamp_duty + null_gst - discount + LCT_amount

    normalized_note = ""
    if gst_mode == "GST exclusive":
        normalized_note = (
            f"(Converted to incl GST: Price ${price:,.2f}, Costs ${costs:,.2f}, "
            f"Discount ${discount:,.2f})"
        )

    return {
        "rounded_price": rounded_price,
        "stamp_duty": stamp_duty,
        "GST": GST,
        "LCT": LCT_amount,
        "Total": Total,
        "normalized_note": normalized_note
    }

# =========================
# UI (Streamlit)
# =========================

# --- Defaults & session reset ---
DEFAULTS = {
    "state": "Queensland",
    "category": "Car/Truck",
    "gst_mode": "GST inclusive",
    "price": 0.0,
    "costs": 0.0,
    "null_gst": 0.0,
    "discount": 0.0,
    "qld_cyl": "electric/hybrid",
    "qld_base": "New/Used",
    "tas_vehicle_type": "passenger (< 9 people and not utes, motor cycles, panel vans)",
    "vic_category_car": "Private (passenger)",
    "vic_category_bike": "Motorcycle (new registration)",
    "lct": "Exempt",
}

def reset_state():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v

if "initialized" not in st.session_state:
    reset_state()
    st.session_state["initialized"] = True

# --- Inputs ---
with st.form("calc_form"):
    col1, col2 = st.columns(2)

    with col1:
        state = st.selectbox(
            "Select State",
            ["Queensland", "New South Wales", "South Australia", "Northern Territory", "Tasmania", "Victoria"],
            index=["Queensland", "New South Wales", "South Australia", "Northern Territory", "Tasmania", "Victoria"].index(
                st.session_state.get("state", DEFAULTS["state"])
            ),
            key="state",
        )

        category = st.selectbox(
            "Category",
            ["Car/Truck", "Motorcycle"],
            index=["Car/Truck", "Motorcycle"].index(
                st.session_state.get("category", DEFAULTS["category"])
            ),
            key="category",
        )

        gst_mode = st.selectbox(
            "Amounts entered are",
            ["GST inclusive", "GST exclusive"],
            index=["GST inclusive", "GST exclusive"].index(
                st.session_state.get("gst_mode", DEFAULTS["gst_mode"])
            ),
            key="gst_mode",
        )

    suf = " " + mode_suffix(st.session_state["gst_mode"])

    with col2:
        price = st.number_input(
            f"Please enter the price and any accessories for stamp duty {suf}",
            min_value=0.0, step=100.0, format="%.2f", key="price"
        )
        costs = st.number_input(
            f"Please add other costs to consider for GST (service plans etc) {suf}",
            min_value=0.0, step=50.0, format="%.2f", key="costs"
        )
        null_gst = st.number_input(
            "Please enter CTP, rego or other costs not having GST",
            min_value=0.0, step=50.0, format="%.2f", key="null_gst"
        )
        discount = st.number_input(
            f"Discount: {suf}",
            min_value=0.0, step=50.0, format="%.2f", key="discount"
        )

    # --- Conditional controls ---
    # Queensland specifics (cars only)
    if state == "Queensland" and category != "Motorcycle":
        st.subheader("Queensland Options")
        qld_cyl = st.selectbox(
            "Vehicle Type (Qld only)",
            ["electric/hybrid", "1-4 cylinders", "5-6 cylinders", "7+ cylinders"],
            index=["electric/hybrid", "1-4 cylinders", "5-6 cylinders", "7+ cylinders"].index(
                st.session_state.get("qld_cyl", DEFAULTS["qld_cyl"])
            ),
            key="qld_cyl"
        )
        qld_base = st.selectbox(
            "Base Type (Qld only)",
            ["New/Used", "GVM"],
            index=["New/Used", "GVM"].index(
                st.session_state.get("qld_base", DEFAULTS["qld_base"])
            ),
            key="qld_base"
        )
    else:
        qld_cyl = st.session_state.get("qld_cyl", DEFAULTS["qld_cyl"])
        qld_base = st.session_state.get("qld_base", DEFAULTS["qld_base"])

    # Tasmania – hide vehicle type if Motorcycle
    if state == "Tasmania" and category != "Motorcycle":
        st.subheader("Tasmania Options")
        tas_vehicle_type = st.selectbox(
            "Vehicle Type (Tas only)",
            [
                "passenger (< 9 people and not utes, motor cycles, panel vans)",
                "commercial up to 4.5t",
                "commercial more than 4.5t",
                "manufacturer fleet discount (except heavy vehicles)"
            ],
            index=0,
            key="tas_vehicle_type"
        )
    else:
        tas_vehicle_type = st.session_state.get("tas_vehicle_type", DEFAULTS["tas_vehicle_type"])

    # Victoria – category menu depends on Motorcycle
    if state == "Victoria":
        st.subheader("Victoria Options")
        if category == "Motorcycle":
            vic_category = st.selectbox(
                "Victoria Category",
                ["Motorcycle (new registration)", "Motorcycle (used/transfer)"],
                index=["Motorcycle (new registration)", "Motorcycle (used/transfer)"].index(
                    st.session_state.get("vic_category_bike", DEFAULTS["vic_category_bike"])
                ),
                key="vic_category_bike"
            )
        else:
            vic_category = st.selectbox(
                "Victoria Category",
                [
                    "Private (passenger)",
                    "Low emission (passenger)",
                    "Primary producer (passenger)",
                    "Commercial (new registration)",
                    "Commercial (used/transfer)",
                    "Demonstrator (passenger)",
                    "Demo commercial (used/transfer)"
                ],
                index=[
                    "Private (passenger)",
                    "Low emission (passenger)",
                    "Primary producer (passenger)",
                    "Commercial (new registration)",
                    "Commercial (used/transfer)",
                    "Demonstrator (passenger)",
                    "Demo commercial (used/transfer)"
                ].index(st.session_state.get("vic_category_car", DEFAULTS["vic_category_car"])),
                key="vic_category_car"
            )
    else:
        # Keep last selected in session for continuity
        vic_category = (
            st.session_state.get("vic_category_bike", DEFAULTS["vic_category_bike"])
            if category == "Motorcycle"
            else st.session_state.get("vic_category_car", DEFAULTS["vic_category_car"])
        )

    # LCT visibility: show only for cars/trucks and if (price+costs-discount) incl GST > 80,567
    price_incl = to_inclusive(price, gst_mode)
    costs_incl = to_inclusive(costs, gst_mode)
    discount_incl = to_inclusive(discount, gst_mode)
    lct_visible = (category != "Motorcycle") and ((price_incl + costs_incl - discount_incl) > 80_567.0)

    if lct_visible:
        st.subheader("Luxury Car Tax")
        lct_selection = st.selectbox(
            "LCT Category",
            ["Fuel Efficient", "Not Fuel Efficient", "Exempt"],
            index=["Fuel Efficient", "Not Fuel Efficient", "Exempt"].index(
                st.session_state.get("lct", DEFAULTS["lct"])
            ),
            key="lct"
        )
    else:
        lct_selection = "Exempt"
        st.session_state["lct"] = "Exempt"

    # Buttons
    colA, colB = st.columns([1, 1])
    with colA:
        submitted = st.form_submit_button("Calculate", use_container_width=True)
    with colB:
        reset = st.form_submit_button("Reset", use_container_width=True)

if reset:
    reset_state()
    st.success("Cleared all fields.")

if submitted:
    res = calculate(
        state=st.session_state["state"],
        category=st.session_state["category"],
        gst_mode=st.session_state["gst_mode"],
        price_entered=st.session_state["price"],
        costs_entered=st.session_state["costs"],
        null_gst=st.session_state["null_gst"],
        discount_entered=st.session_state["discount"],
        qld_cyl=st.session_state.get("qld_cyl", DEFAULTS["qld_cyl"]),
        qld_base=st.session_state.get("qld_base", DEFAULTS["qld_base"]),
        tas_vehicle_type=st.session_state.get("tas_vehicle_type", DEFAULTS["tas_vehicle_type"]),
        vic_category=(
            st.session_state.get("vic_category_bike", DEFAULTS["vic_category_bike"])
            if st.session_state["category"] == "Motorcycle"
            else st.session_state.get("vic_category_car", DEFAULTS["vic_category_car"])
        ),
        lct_selection=st.session_state.get("lct", "Exempt"),
    )

    st.markdown("### Results")
    if res["normalized_note"]:
        st.info(res["normalized_note"])

    c1, c2, c3 = st.columns(3)
    c1.metric("Rounded Amount Used for Stamp Duty", f"${res['rounded_price']:,.2f}")
    c2.metric("Stamp Duty", f"${res['stamp_duty']:,.2f}")
    c3.metric("LCT", f"${res['LCT']:,.2f}")

    c4, c5 = st.columns(2)
    c4.metric("GST", f"${res['GST']:,.2f}")
    c5.metric("Total Purchase Price", f"${res['Total']:,.2f}")

    st.caption("Help: Change inputs and click **Calculate**. Use **Reset** to clear all fields.")
else:
    st.write("👉 Enter details above and click **Calculate**.")
