"""Tests for timelink.linking.normalize (MHK-faithful normalizers)."""

# pylint: disable=import-error
from timelink.linking.normalize import (
    break_name,
    count_interrog,
    fold_text,
    is_name_particle,
    is_place_particle,
    normalize_civil_status,
    normalize_place,
    split_person_name,
    strip_commas,
    strip_interrog,
)


class TestBreakName:
    def test_mhk_example(self):
        # the example from the MHK names.sql header comment
        assert break_name("joaquim carvalho") == ("joaquim", "carvalho")

    def test_splits_at_first_space(self):
        assert break_name("maria de sousa") == ("maria", "de sousa")

    def test_single_word(self):
        assert break_name("joaquim") == ("joaquim", "")

    def test_leading_whitespace_and_collapse(self):
        assert break_name("  maria   de  sousa") == ("maria", "de  sousa")

    def test_empty(self):
        assert break_name("") == ("", "")
        assert break_name(None) == ("", "")


class TestParticles:
    def test_name_particles_pt(self):
        for token in ("da", "de", "do", "das", "dos", "a", "e", "o"):
            assert is_name_particle(token), token
        assert not is_name_particle("carvalho")
        assert not is_name_particle("joaquim")

    def test_place_particles_include_name_particles_plus_places(self):
        assert is_place_particle("casal")
        assert is_place_particle("quinta")
        assert is_place_particle("sao")
        assert not is_place_particle("aveiro")

    def test_other_languages(self):
        assert not is_name_particle("de", lang="EN")
        assert not is_place_particle("sao", lang="EN")


class TestValueCleaners:
    def test_strip_commas(self):
        assert strip_commas("coimbra, portugal") == "coimbra  portugal"
        assert strip_commas("no commas") == "no commas"

    def test_strip_interrog(self):
        assert strip_interrog("joaquim?") == "joaquim"
        assert strip_interrog("maria? da silva?") == "maria da silva"

    def test_count_interrog(self):
        assert count_interrog("joaquim?") == 1
        assert count_interrog("maria??") == 2
        assert count_interrog("certo") == 0


class TestNormalizePlace:
    def test_drops_particles(self):
        assert normalize_place("casal da boa vista") == "boa vista"
        assert normalize_place("quinta de sao joao") == "joao"

    def test_keeps_regular_words(self):
        assert normalize_place("aveiro") == "aveiro"
        assert normalize_place("boa vista") == "boa vista"

    def test_strips_commas_and_collapses(self):
        assert normalize_place("oliveira,  do conde") == "oliveira conde"


class TestCivilStatus:
    def test_mhk_prefixes(self):
        # normalize_civil_status: solt* -> s, cas* -> c, viuv* -> v
        assert normalize_civil_status("solteiro") == "s"
        assert normalize_civil_status("solteira") == "s"
        assert normalize_civil_status("casado") == "c"
        assert normalize_civil_status("casada") == "c"
        assert normalize_civil_status("viuvo") == "v"
        assert normalize_civil_status("viuva") == "v"

    def test_uncertainty_marker_stripped_first(self):
        assert normalize_civil_status("solteiro?") == "s"

    def test_case_insensitive(self):
        assert normalize_civil_status("Casado") == "c"

    def test_unknown_value_lowered(self):
        assert normalize_civil_status("Desconhecido") == "desconhecido"


class TestSplitPersonName:
    def test_given_name_and_surname(self):
        assert split_person_name("joaquim carvalho") == {
            "first_name": "joaquim", "surname": ["carvalho"]}

    def test_particles_join_surname(self):
        assert split_person_name("joaquim de carvalho") == {
            "first_name": "joaquim", "surname": ["de", "carvalho"]}
        assert split_person_name("maria das dores santos") == {
            "first_name": "maria", "surname": ["das", "dores", "santos"]}

    def test_single_name(self):
        assert split_person_name("joaquim") == {
            "first_name": "joaquim", "surname": []}


class TestFoldText:
    def test_lowercase(self):
        assert fold_text("Joaquim Carvalho") == "joaquim carvalho"

    def test_accent_folded(self):
        assert fold_text("João Corção") == "joao corcao"
        assert fold_text("ílhavo") == "ilhavo"

    def test_whitespace_collapsed(self):
        assert fold_text("  boa\n\t vista  ") == "boa vista"

    def test_empty(self):
        assert fold_text("") == ""
