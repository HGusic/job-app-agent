from src.experience_mapper import map_education_field, map_work_field


def test_work_field_mapping():
    assert map_work_field("Job Title") == "title"
    assert map_work_field("Company Name") == "company"
    assert map_work_field("From") == "start"
    assert map_work_field("To") == "end"
    assert map_work_field("Role Description") == "description"
    assert map_work_field("I currently work here") == "current"


def test_education_field_mapping():
    assert map_education_field("School") == "school"
    assert map_education_field("Degree") == "degree"
    assert map_education_field("Field of Study") == "specialization"
    assert map_education_field("Major") == "specialization"
    assert map_education_field("Concentration") == "specialization"
