"""utils for building urlpatterns."""

from django.urls import path

import inflect

from rest_framework_json_api.relations import ResourceRelatedField

engine = inflect.engine()


def resource_relationships(name, view):
    """Add a path for an resource relationships."""
    return path(
        '%s/<int:pk>/relationships/<related_field>' % name,
        view,
        name='%s-relationships' % name,
    )


def one_to_one_relationship(name, relation, viewset):
    """Return urls for a one to one relationship."""
    return path(
        '%s/<int:%s_pk>/%s' % (
            engine.plural(name),
            name,
            relation,
        ),
        viewset.as_view({'get': 'retrieve'}),
        name='%s-%s-detail' % (
            name,
            relation,
        ),
    )


def resource_related_field(
    model,
    name,
    relationship,
    many=True,
    required=False,
    read_only=False,
):
    """Generate a ResourceRelatedField for given resource and relationship."""
    kwargs = {}
    if not read_only:
        kwargs['queryset'] = model.objects
    return ResourceRelatedField(
        many=many,
        related_link_view_name='%s-%s-%s' % (
            name,
            relationship,
            'list' if many else 'detail',
        ),
        related_link_url_kwarg='%s_pk' % name,
        required=required,
        read_only=read_only,
        **kwargs,
    )
