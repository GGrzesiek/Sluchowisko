from pipeline.geo import haversine_m, norm_name, slugify

ONE_DEGREE_LATITUDE_M = 111_195


def test_haversine_zero():
    assert haversine_m(52.23, 21.01, 52.23, 21.01) == 0


def test_haversine_one_degree_of_latitude():
    assert abs(haversine_m(52.0, 21.0, 53.0, 21.0) - ONE_DEGREE_LATITUDE_M) < 200


def test_slugify_polish():
    assert slugify("Żerań Wschodni") == "zeran-wschodni"
    assert slugify("Inowłodzka") == "inowlodzka"
    assert slugify("Rondo Żaba") == "rondo-zaba"


def test_norm_name_ignores_case_and_spaces():
    assert norm_name("metro  BRÓDNO") == norm_name("Metro Bródno")
