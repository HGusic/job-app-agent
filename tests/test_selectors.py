from src.selectors import css_escape_attr, locator_by_id


def test_css_escape_attr():
    assert css_escape_attr('foo"bar') == 'foo\\"bar'
    assert css_escape_attr("experienceData[0].fromTo.startDate") == "experienceData[0].fromTo.startDate"
