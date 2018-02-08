from django.contrib import admin

import django.db.models as django_models
import mgmembers.models as mgmodels

EXCLUDE_MODELS = set([])


def register_models(models, namespace=None):
    models = iter(models.__dict__.items())

    for name, value in models:
        # Skip stuff that is not classes
        if not isinstance(value, type):
            continue

        # Skip stuff that is not models
        if not issubclass(value, django_models.Model):
            continue

        if value._meta.abstract:
            continue

        # Skip stuff that is not native to the booking.models module
        if namespace is not None and not value.__module__ == namespace:
            continue

        if value in EXCLUDE_MODELS:
            continue

        admin.site.register(value)


register_models(mgmodels, 'mgmembers.models')
