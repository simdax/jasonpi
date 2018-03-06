"""Test utils functions for urls."""

from .. import reload


def test_resource_relationships(mocker):
    """Test that resource_relationships use path."""
    path = mocker.patch('django.urls.path', return_value='ok')
    reload('utils.urls')
    from ..urls import resource_relationships

    name = 'name'

    def view(request):
        """Fake view."""
        pass

    p = resource_relationships(name, view)

    assert p == 'ok'
    path.assert_called_once_with(
        '%s/<int:pk>/relationships/<related_field>' % name,
        view,
        name='%s-relationships' % name,
    )
