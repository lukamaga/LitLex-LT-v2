import pytest

from ltnum import amounts, ranges, stated, to_int


@pytest.mark.parametrize("phrase, value", [
    ("aštuoniasdešimt", 80),
    ("dviejų šimtų", 200),
    ("vieno šimto keturiasdešimt", 140),
    ("trijų šimtų dvidešimt", 320),
    ("vieno tūkstančio keturių šimtų penkiasdešimt", 1450),
    ("dviejų tūkstančių", 2000),
    ("šeši tūkstančiai", 6000),
    ("dešimt", 10),
    ("vienuolikos", 11),
    ("dvylikos", 12),
    ("trylikos", 13),
    ("devyniasdešimties", 90),
    ("šimto", 100),
])
def test_to_int(phrase, value):
    assert to_int(phrase) == value


def test_ranges_and_amounts():
    text = ("užtraukia baudą asmenims nuo aštuoniasdešimt iki dviejų šimtų eurų ir juridinių asmenų vadovams "
            "arba kitiems atsakingiems asmenims \u2013 nuo dviejų šimtų iki trijų šimtų eurų.")
    assert ranges(text) == [(80, 200), (200, 300)]
    assert amounts(text) == [80, 200, 200, 300]


def test_range_without_nuo_and_upper_bound_only():
    text = "užtraukia baudą vieno šimto keturiasdešimt iki keturių šimtų keturiasdešimt eurų"
    assert ranges(text) == [(140, 440)]
    assert amounts("bauda iki trijų šimtų eurų") == [300]


def test_words_that_only_look_like_numbers():
    assert amounts("Lietuvos Respublika skiria baudą nuo dešimt iki dvylikos eurų") == [10, 12]
    with pytest.raises(ValueError):
        to_int("Respublika")


def test_bounds_written_in_words():
    text = ("Pagal šį kodeksą asmeniui gali būti skiriama ne mažesnė negu dešimt ir ne didesnė negu šeši tūkstančiai "
            "eurų bauda. Administraciniu nurodymu gali būti paskirta ne mažesnė negu penkių eurų bauda.")
    assert ranges(text) == [(10, 6000)]
    assert amounts(text) == [10, 6000, 5]


def test_range_with_euro_word_after_the_lower_bound():
    text = ("užtraukia baudą asmenims nuo penkių šimtų iki vieno tūkstančio eurų ir juridinių asmenų vadovams "
            "ar kitiems atsakingiems asmenims nuo aštuonių šimtų eurų iki vieno tūkstančio penkių šimtų eurų.")
    assert ranges(text) == [(500, 1000), (800, 1500)]
    assert amounts(text) == [500, 1000, 800, 1500]


def test_upper_bound_only_is_a_range_from_zero():
    text = ("skiriama teismo nutartimi fiziniams asmenims iki trijų šimtų eurų, "
            "institucijų atstovams iki šešių šimtų eurų.")
    assert ranges(text) == [(0, 300), (0, 600)]


def test_fines_stated_in_an_answer():
    assert stated("Bauda nuo 300 iki 1 450 eurų.") == ([(300, 1450)], [])
    assert stated("Bauda 80\u2013200 EUR, o vadovams 200-300 eurų.") == ([(80, 200), (200, 300)], [])
    assert stated("Bauda nuo aštuoniasdešimt iki dviejų šimtų eurų.") == ([(80, 200)], [])
    assert stated("Greičio viršijimas daugiau kaip 50 km/h, bauda 450 eurų.") == ([], [450])
    assert stated("Pagal ANK 416 str. 6 d. 2026 m. sausio 12 d.") == ([], [])


@pytest.mark.parametrize("text, expected", [
    ("asmeniui gresia bauda iki 300 eurų", ([(0, 300)], [])),
    ("ne mažiau kaip 80 eurų ir ne daugiau kaip 300 eurų", ([(80, 300)], [])),
    ("ne mažesnė negu dvidešimt ir ne didesnė negu devyni šimtai eurų", ([(20, 900)], [])),
    ("bauda nuo 3 iki 5 tūkst. eurų", ([(3000, 5000)], [])),
    ("bauda 1,5 tūkst. eurų", ([], [1500])),
    ("nuo EUR 3000 iki EUR 5000", ([(3000, 5000)], [])),
    ("bauda nuo 80,00 iki 200,00 eurų", ([(80, 200)], [])),
    ("bauda 1 400,50 eurų", ([], [1400.5])),
    ("nuo 2026-11-01 \u2013 80 eurų", ([], [80])),
    ("taikoma visose 27 Europos Sąjungos šalyse", ([], [])),
    ("o pakartotinai tris šimtus eurų", ([], [300])),
    ("kai pavogta prekių už keliasdešimt eurų, bauda nuo 90 iki 400 eurų", ([(90, 400)], [])),
])
def test_more_ways_of_writing_a_fine(text, expected):
    assert stated(text) == expected
