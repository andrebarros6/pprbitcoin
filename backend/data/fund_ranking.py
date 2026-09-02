"""
Market position of the covered PPR funds, by assets under management.

AUM is the right size metric here: PPRs are not exchange-traded, so there is
no order-book volume, and it is what APFIPP itself uses to size the industry.
Figures are from the Investing.com fund listing, August 2026, and are recorded
in DATA_SOURCES.md alongside the rest of the market context.

The published table lists share classes separately (IMGA Poupanca A and R are
one product at EUR 404.3m, not two funds), so ranks here are assigned after
deduplicating by product. That makes "5 of the top 10" a claim about products,
which is what a saver choosing a fund actually cares about.

Funds absent from this map are not ranked -- they sit outside the top 10, or
their AUM is not published -- and sort after the ranked ones by name.
"""
from typing import Dict, Optional

# Rank by AUM among Portuguese PPR products, share classes deduplicated.
# Only the funds this tool actually covers appear here; the gaps are the
# products we do not have data for (BPI at #1, Caixa at #6).
_RANK_BY_NAME: Dict[str, int] = {
    "IMGA Poupança PPR": 2,
    "Alves Ribeiro PPR": 3,
    "Casa Global Value PPR Founders": 4,
    "Optimize PPR Agressivo": 8,
}

# Where a fund sits when it has no published rank. Large enough to sort after
# every real rank, small enough to stay well inside an int column.
UNRANKED = 9999


def rank_for(nome: str) -> Optional[int]:
    """
    Market rank by AUM for a fund, or None when it is not in the top 10.

    Args:
        nome: The fund's name as stored in the database.

    Returns:
        The 1-based rank, or None if unranked.
    """
    return _RANK_BY_NAME.get(nome)


def sort_key(nome: str) -> tuple:
    """
    Ordering key placing ranked funds first, then the rest alphabetically.

    Args:
        nome: The fund's name as stored in the database.

    Returns:
        A tuple suitable for sorted(key=...).
    """
    return (rank_for(nome) or UNRANKED, nome)
