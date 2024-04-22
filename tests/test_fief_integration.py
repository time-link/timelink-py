from timelink.app.services.auth import get_fief_container


def test_get_fief_container():
    container = get_fief_container(all=True, filters={'name': 'fief-server'})
    assert container is not None
