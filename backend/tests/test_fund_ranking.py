"""
Tests for ordering funds by market position.

The ranking is keyed on fund names copied from an external table, so the
failure mode worth guarding is a name that silently stops matching -- a fund
would quietly lose its rank and drop to the bottom of the list with no error.
"""
from data.fund_ranking import UNRANKED, rank_for, sort_key, _RANK_BY_NAME


class TestRankLookup:
    def test_known_fund_has_rank(self):
        assert rank_for("Alves Ribeiro PPR") == 3

    def test_unknown_fund_has_no_rank(self):
        assert rank_for("Optimize PPR Moderado") is None

    def test_unknown_name_does_not_raise(self):
        assert rank_for("Fundo Que Nao Existe") is None

    def test_ranks_are_unique(self):
        """Two funds sharing a rank would make the order arbitrary."""
        ranks = list(_RANK_BY_NAME.values())
        assert len(ranks) == len(set(ranks))

    def test_ranks_are_plausible_top_ten_positions(self):
        assert all(1 <= r <= 10 for r in _RANK_BY_NAME.values())


class TestSorting:
    def test_ranked_funds_come_first(self):
        names = [
            "Optimize PPR Moderado",       # unranked
            "Alves Ribeiro PPR",           # 3
            "EuroBic PPR Ciclo de Vida +55",  # unranked
            "IMGA Poupança PPR",           # 2
        ]
        assert sorted(names, key=sort_key)[:2] == [
            "IMGA Poupança PPR",
            "Alves Ribeiro PPR",
        ]

    def test_ranked_order_is_ascending(self):
        ordered = sorted(_RANK_BY_NAME, key=sort_key)
        assert [rank_for(n) for n in ordered] == sorted(_RANK_BY_NAME.values())

    def test_unranked_funds_sort_alphabetically(self):
        names = ["Zeta PPR", "Alfa PPR", "Meio PPR"]
        assert sorted(names, key=sort_key) == ["Alfa PPR", "Meio PPR", "Zeta PPR"]

    def test_unranked_sort_key_uses_sentinel(self):
        assert sort_key("Fundo Desconhecido")[0] == UNRANKED

    def test_sentinel_sorts_after_every_real_rank(self):
        assert UNRANKED > max(_RANK_BY_NAME.values())
