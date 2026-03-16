"""Portfolio Management Page — PAGE-002.

Tabs: Holdings | Add Holding | Transactions | Accounts
"""

import asyncio
from datetime import date

import pandas as pd
import streamlit as st

from finapp.app.services.portfolio_service import PortfolioService


def render_portfolio() -> None:
    """Render the Portfolio Management page."""
    st.title("💼 My Portfolio")

    portfolio_service = PortfolioService()

    tab_holdings, tab_add, tab_transactions, tab_accounts = st.tabs(
        ["📋 Holdings", "➕ Add Holding", "📜 Transactions", "🏦 Accounts"]
    )

    # -------------------------------------------------------------------------
    # TAB: Holdings
    # -------------------------------------------------------------------------
    with tab_holdings:
        with st.spinner("Loading holdings..."):
            portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())

        all_holdings = []
        for account in portfolio.accounts:
            for holding in account.holdings:
                if holding.is_open:
                    all_holdings.append({
                        "Account": account.name,
                        "Ticker": holding.ticker,
                        "Asset Class": holding.asset_class,
                        "Quantity": float(holding.quantity),
                        "Cost Basis/Share": float(holding.cost_basis_per_share),
                        "Total Cost Basis": float(holding.total_cost_basis),
                        "Purchase Date": str(holding.purchase_date),
                        "Days Held": holding.holding_period_days,
                        "Long Term": "✅" if holding.is_long_term else "❌",
                        "Notes": holding.notes or "",
                    })

        if all_holdings:
            df = pd.DataFrame(all_holdings)
            st.dataframe(df, use_container_width=True, hide_index=True)

            col1, col2 = st.columns([1, 4])
            with col1:
                if st.button("📥 Export CSV"):
                    from finapp.mcp_servers.export_server import export_portfolio_csv
                    portfolio_dict = asyncio.run(
                        asyncio.coroutine(
                            lambda: asyncio.run(
                                _get_portfolio_dict(portfolio_service)
                            )
                        )()
                    )
        else:
            st.info("No holdings yet. Use the **Add Holding** tab to add your first position.")

    # -------------------------------------------------------------------------
    # TAB: Add Holding
    # -------------------------------------------------------------------------
    with tab_add:
        st.subheader("Add a New Holding")

        with st.form("add_holding_form"):
            col1, col2 = st.columns(2)
            with col1:
                ticker = st.text_input("Ticker Symbol *", placeholder="e.g. AAPL", max_chars=10)
                asset_class = st.selectbox(
                    "Asset Class *",
                    options=["equity", "etf", "mutual_fund", "bond", "crypto", "cash", "reit", "commodity", "other"],
                )
                quantity = st.number_input("Quantity *", min_value=0.0001, step=0.001, format="%.4f")

            with col2:
                cost_basis = st.number_input("Cost Basis per Share ($) *", min_value=0.0, step=0.01, format="%.2f")
                purchase_date = st.date_input("Purchase Date *", value=date.today(), max_value=date.today())

                # Account selector
                portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())
                account_options = {acc.name: acc.id for acc in portfolio.accounts if acc.is_active}
                if account_options:
                    selected_account_name = st.selectbox("Account *", options=list(account_options.keys()))
                    selected_account_id = account_options[selected_account_name]
                else:
                    st.info("No accounts found — a default account will be created.")
                    selected_account_id = None

            notes = st.text_area("Notes (optional)", max_chars=1000, height=80)
            submitted = st.form_submit_button("➕ Add Holding", type="primary")

        if submitted:
            if not ticker:
                st.error("Ticker symbol is required.")
            elif quantity <= 0:
                st.error("Quantity must be greater than 0.")
            elif cost_basis < 0:
                st.error("Cost basis cannot be negative.")
            else:
                try:
                    with st.spinner("Adding holding..."):
                        asyncio.run(portfolio_service.add_holding(
                            ticker=ticker,
                            quantity=quantity,
                            cost_basis_per_share=cost_basis,
                            purchase_date=purchase_date,
                            asset_class=asset_class,
                            account_id=selected_account_id,
                            notes=notes or None,
                        ))
                    st.success(f"✅ Added {quantity:.4f} shares of {ticker.upper()} to your portfolio!")
                    st.rerun()
                except ValueError as exc:
                    st.error(f"Validation error: {exc}")
                except Exception as exc:
                    st.error(f"Failed to add holding: {exc}")

    # -------------------------------------------------------------------------
    # TAB: Transactions
    # -------------------------------------------------------------------------
    with tab_transactions:
        st.subheader("Transaction History")

        from finapp.infrastructure.repositories.portfolio_repository import TransactionRepository
        tx_repo = TransactionRepository()

        # Filters
        fcol1, fcol2, fcol3 = st.columns(3)
        with fcol1:
            filter_ticker = st.text_input("Filter by Ticker", placeholder="e.g. AAPL")
        with fcol2:
            filter_types = st.multiselect(
                "Transaction Types",
                options=["buy", "sell", "dividend", "transfer_in", "transfer_out", "split"],
                default=[],
            )
        with fcol3:
            tx_limit = st.number_input("Max Records", min_value=10, max_value=500, value=100)

        with st.spinner("Loading transactions..."):
            transactions = asyncio.run(tx_repo.list_transactions(
                ticker=filter_ticker.upper() if filter_ticker else None,
                transaction_types=filter_types if filter_types else None,
                limit=int(tx_limit),
            ))

        if transactions:
            tx_data = [{
                "Date": str(t.transaction_date),
                "Type": t.transaction_type.capitalize(),
                "Ticker": t.ticker,
                "Quantity": float(t.quantity),
                "Price": f"${float(t.price_per_share):.2f}",
                "Total": f"${float(t.total_amount):,.2f}",
                "Fees": f"${float(t.fees):.2f}",
                "Notes": t.notes or "",
            } for t in transactions]
            st.dataframe(pd.DataFrame(tx_data), use_container_width=True, hide_index=True)
        else:
            st.info("No transactions found with the current filters.")

    # -------------------------------------------------------------------------
    # TAB: Accounts
    # -------------------------------------------------------------------------
    with tab_accounts:
        st.subheader("Accounts")

        with st.spinner("Loading accounts..."):
            portfolio = asyncio.run(portfolio_service.get_or_create_portfolio())

        if portfolio.accounts:
            acc_data = [{
                "Account Name": acc.name,
                "Type": acc.account_type,
                "Currency": acc.currency,
                "Holdings": acc.holdings_count,
                "Status": "Active" if acc.is_active else "Inactive",
            } for acc in portfolio.accounts]
            st.dataframe(pd.DataFrame(acc_data), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Add New Account")
        with st.form("add_account_form"):
            acc_name = st.text_input("Account Name *", placeholder="e.g. Fidelity Brokerage", max_chars=100)
            acc_type = st.selectbox("Account Type *", options=["brokerage", "ira", "roth_ira", "401k", "crypto", "savings", "other"])
            acc_currency = st.selectbox("Currency", options=["USD", "EUR", "GBP", "CAD", "AUD"])
            acc_submitted = st.form_submit_button("Add Account")

        if acc_submitted:
            if not acc_name:
                st.error("Account name is required.")
            else:
                with st.spinner("Creating account..."):
                    asyncio.run(portfolio_service.create_account(acc_name, acc_type, acc_currency))
                st.success(f"✅ Account '{acc_name}' created!")
                st.rerun()


async def _get_portfolio_dict(service: PortfolioService) -> dict:
    from finapp.mcp_servers.portfolio_server import get_portfolio
    return await get_portfolio()


if __name__ == "__main__":
    render_portfolio()
