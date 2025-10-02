import pytest
from timelink.web.pages.display_id_page import DisplayIDPage
from nicegui.testing import User
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace


pytest_plugins = ["nicegui.testing.plugin", "nicegui.testing.user_plugin"]


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_class", ["person", "geoentity", "act"])
async def test_display_id_init(user: User, fake_db, fake_kserver, entity_class):
    """Test if display page is being properly initialized."""

    # Mock entity
    fake_entity = SimpleNamespace(pom_class=entity_class, name=f"Test {entity_class}")

    fake_db.session.return_value.__enter__.return_value = fake_db
    fake_db.get_entity.return_value = fake_entity

    page = DisplayIDPage(fake_db, fake_kserver)
    page.register()

    assert page.database is fake_db
    assert page.kserver is fake_kserver

    await user.open("/id/test-id")

    fake_db.get_entity.assert_called_once_with("test-id", session=fake_db)


@pytest.mark.asyncio
async def test_display_id_not_found(user: User, fake_db, fake_kserver):
    """Test failure state when entity is not found."""

    fake_db.session.return_value.__enter__.return_value = fake_db
    fake_db.get_entity.return_value = None

    page = DisplayIDPage(fake_db, fake_kserver)
    page.register()

    await user.open("/id/missing-id")

    fake_db.get_entity.assert_called_once_with("missing-id", session=fake_db)

    # Assert the error message is rendered
    user.find("No entity with value missing-id found.")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "pom_class, func_name",
    [
        ("person", "_display_person"),
        ("geoentity", "_display_geoentity"),
        ("act", "_display_act"),
    ],
)
async def test_display_id_dispatch(user, fake_db, fake_kserver, monkeypatch, pom_class, func_name):
    """Test that the correct display function is called for each class."""

    fake_entity = SimpleNamespace(pom_class=pom_class, name=f"Test {pom_class}")

    fake_db.session.return_value.__enter__.return_value = fake_db
    fake_db.get_entity.return_value = fake_entity

    mock_display = AsyncMock()
    monkeypatch.setattr(DisplayIDPage, func_name, mock_display)

    page = DisplayIDPage(fake_db, fake_kserver)
    page.register()

    await user.open("/id/test-id")

    fake_db.get_entity.assert_called_once_with("test-id", session=fake_db)
    mock_display.assert_awaited_once_with(fake_entity)


@pytest.mark.asyncio
async def test_display_person(user: User, fake_db, fake_kserver, monkeypatch):
    """Check if display_person renders as expected."""

    fake_entity = SimpleNamespace(
        id="test-id", name="John Doe", groupname="grp", sex="M", the_line="10", pom_class="person"
    )

    fake_db.session.return_value.__enter__.return_value = fake_db
    fake_db.get_entity.return_value = fake_entity

    # Fake parsed details
    fake_attrs = {"15010827": [SimpleNamespace(the_type="residencia", the_value="casa velha", obs="")]}

    fake_rels_in = [
        {
            "id": "test-relation-in-1",
            "origin": "test-rel-out-id-1",
            "destination": "test-id",
            "the_type": "parentesco",
            "the_value": "mae",
            "the_date": "15500421",
            "obs": "",
            "org_name": "test mom",
        }
    ]

    fake_rels_out = [
        {
            "id": "test-relation",
            "origin": "test-origin",
            "destination": "test-destination",
            "the_type": "parentesco",
            "the_value": "pai",
            "the_date": "16850827",
            "obs": "",
            "dest_name": "test-daughter",
        },
        {
            "id": "test-relation-2",
            "origin": "test-origin",
            "destination": "test-destination-2",
            "the_type": "bap",
            "the_value": "n",
            "the_date": "16850823",
            "obs": "",
            "dest_name": "bap",
        },  # should appear in functions
    ]

    mock_parse = MagicMock(return_value=(fake_attrs, fake_rels_in, fake_rels_out))
    monkeypatch.setattr("timelink.web.pages.display_id_page.timelink_web_utils.parse_entity_details", mock_parse)

    page = DisplayIDPage(database=fake_db, kserver=fake_kserver)
    page.register()

    await user.open("/id/test-id")

    # --- Assertions ---
    mock_parse.assert_called_once_with(fake_entity)

    # User sees page header
    await user.should_see(fake_entity.name)
    await user.should_see(f"id: {fake_entity.id}")
    await user.should_see("groupname:")
    await user.should_see(fake_entity.groupname)
    await user.should_see("sex:")
    await user.should_see(fake_entity.sex)
    await user.should_see("line:")
    await user.should_see(fake_entity.the_line)

    # User sees proper date
    await user.should_see("1501-08-27")

    # User sees functions
    await user.should_see("bap : n")

    # User sees attributes
    await user.should_see("residencia")
    await user.should_see(":")
    await user.should_see("casa velha")

    # User sees rels-in
    await user.should_see("tem como")
    await user.should_see("mae")
    await user.should_see(" : ")
    await user.should_see("test mom")

    # User sees rels-out
    await user.should_see("pai")
    await user.should_see("de:")
    await user.should_see("test-daughter")


@pytest.mark.asyncio
async def test_display_geoentity(user, fake_db, fake_kserver, monkeypatch):
    """Check if display_geoentity renders as expected."""

    fake_entity = SimpleNamespace(id="geo-1", name="Lisbon", inside="geo-file-1", pom_class="geoentity")

    fake_origin_entity = SimpleNamespace(id="geo-2", name="Portugal", inside="geo-file-1", pom_class="geoentity")

    fake_db.session.return_value.__enter__.return_value = fake_db

    # Side effect to return different entities depending on ID
    def get_entity_side_effect(entity_id, session=None):
        if entity_id == "geo-1":
            return fake_entity
        elif entity_id in ("origin-1", "origin-2"):
            return fake_origin_entity
        return SimpleNamespace(id=entity_id, name="Unknown", pom_class="geoentity")

    fake_db.get_entity.side_effect = get_entity_side_effect

    # Fake parsed details
    fake_attrs = {"1500-01-01": [SimpleNamespace(the_type="geografica", the_value="pertence região", obs="")]}

    fake_rels_in = [
        {
            "id": "rel-in-1",
            "origin": "origin-1",
            "destination": "geo-1",
            "the_type": "geografica",
            "the_value": "pertence região",
            "the_date": "0",
            "obs": "",
            "org_name": "geotest",
        }
    ]

    fake_rels_out = [
        {
            "id": "rel-out-1",
            "origin": "origin-2",
            "destination": "geo-2",
            "the_type": "geografica",
            "the_value": "pertence região",
            "the_date": "16440000",
            "obs": "",
            "dest_name": "destname-test",
        },
        {
            "id": "rel-out-invalid",
            "origin": "origin-3",
            "destination": "geo-id-3",
            "the_type": "invalid-rel-type",
            "the_value": "geo1",
            "the_date": "0",
            "obs": "",
            "dest_name": "geodesc",
        },
    ]

    mock_parse = MagicMock(return_value=(fake_attrs, fake_rels_in, fake_rels_out))
    monkeypatch.setattr(
        "timelink.web.pages.display_id_page.timelink_web_utils.parse_entity_details",
        mock_parse,
    )

    page = DisplayIDPage(database=fake_db, kserver=fake_kserver)
    page.register()

    await user.open("/id/geo-1")

    # --- Assertions ---
    mock_parse.assert_called_once_with(fake_entity)

    # Header content
    await user.should_see("Lisbon")
    await user.should_see("id:")
    await user.should_see("geo-1")
    await user.should_see("inside:")
    await user.should_see("geo-file-1")

    # Attributes
    await user.should_see("geografica")
    await user.should_see(":")
    await user.should_see("pertence região")

    # Relations in
    await user.should_see("tem como")
    await user.should_see("pertence região")
    await user.should_see(" : ")
    await user.should_see("Portugal")

    # Relations out
    await user.should_see("pertence região")
    await user.should_see("de")
    await user.should_see("Portugal")

    # Functions
    await user.should_see("geodesc : geo1")


@pytest.mark.asyncio
async def test_display_act(user, fake_db, fake_kserver, monkeypatch):
    """Check if _display_act renders header and body as expected."""

    fake_entity = SimpleNamespace(id="act-1", the_type="act", pom_class="act")

    fake_db.session.return_value.__enter__.return_value = fake_db
    fake_db.get_entity.return_value = fake_entity

    page = DisplayIDPage(database=fake_db, kserver=fake_kserver)
    page.register()

    # Mock templates
    mock_header_template = MagicMock()
    mock_header_template.render.return_value = "<div>header content</div>"

    mock_body_template = MagicMock()
    mock_body_template.render.return_value = "<div>body content</div>"

    def get_template_mock(name):
        if "header" in name:
            return mock_header_template
        else:
            return mock_body_template

    monkeypatch.setattr("timelink.web.pages.display_id_page.env.get_template", get_template_mock)

    # Mock async function _collect_all_ids
    monkeypatch.setattr(
        "timelink.web.pages.display_id_page.DisplayIDPage._collect_all_ids",
        AsyncMock(return_value=["child1", "child2"]),
    )

    # Run the function
    await user.open("/id/act-1")

    # Assertions
    mock_header_template.render.assert_any_call(entity_title="act", entity=fake_entity)
    mock_body_template.render.assert_any_call(entity_childs=["child1", "child2"])

    # Check if html is being added to the body successfully
    added_html = []

    def fake_add_body_html(html):
        added_html.append(html)

    monkeypatch.setattr("timelink.web.pages.display_id_page.ui.add_body_html", fake_add_body_html)

    # Run again with fake_add_body_html
    await user.open("/id/act-1")
    assert "<div>header content</div>" in added_html
    assert "<div>body content</div>" in added_html


def test_parse_act_header_string(monkeypatch):
    """Check if header parser is rendering HTML for jinja correctly."""

    fake_entity = SimpleNamespace(
        id="act-1",
        the_type="important-act",
        pom_class="act",
        inside="act-list-file",
        groupname="baptismo",
        extra_info={
            "id": {"kleio_element_class": "id"},
            "obs": {"kleio_element_class": "obs", "comment": "(extra note)"},
        },
        obs="this is an observation",
    )

    monkeypatch.setattr(
        "timelink.web.pages.display_id_page.EntityAttrRelSchema.model_validate",
        lambda e: SimpleNamespace(
            model_dump=lambda exclude=None: {
                "groupname": "baptismo",
                "extra_info": fake_entity.extra_info,
            }
        ),
    )

    page = DisplayIDPage(None, None)
    result = page._parse_act_header_string(fake_entity)

    assert "<strong>baptismo</strong>$ important-act" in result
    assert "obs=this is an observation(extra note)" in result
    assert "/inside=" in result
    assert "'/id/act-list-file'\">act-list-file" in result


def test_parse_act_body_strings(monkeypatch):
    """Check if body parser is rendering HTML for jinja correctly."""

    ent_dict = {
        "id": "p1",
        "groupname": "relation",
        "level": 1,
        "extra_attrs": {
            "type": "parentesco",
            "value": "pai",
            "destination": "p2",
            "date": "16850827",
        },
    }

    monkeypatch.setattr(
        "timelink.web.pages.display_id_page.timelink_web_utils.highlight_link", lambda url, label: f"<a>{label}</a>"
    )
    monkeypatch.setattr("timelink.kleio.utilities.format_timelink_date", lambda d: "1685-08-27")

    page = DisplayIDPage(None, None)
    result = page._parse_act_body_strings(ent_dict)

    assert "parentesco" in result
    assert "pai" in result
    assert "1685-08-27" in result
