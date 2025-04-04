# Generated by Django 5.1.5 on 2025-03-10 17:15

import django.db.models.functions.datetime
from django.db import migrations, models

from sentry.new_migrations.migrations import CheckedMigration


class Migration(CheckedMigration):
    # This flag is used to mark that a migration shouldn't be automatically run in production.
    # This should only be used for operations where it's safe to run the migration after your
    # code has deployed. So this should not be used for most operations that alter the schema
    # of a table.
    # Here are some things that make sense to mark as post deployment:
    # - Large data migrations. Typically we want these to be run manually so that they can be
    #   monitored and not block the deploy for a long period of time while they run.
    # - Adding indexes to large tables. Since this can take a long time, we'd generally prefer to
    #   run this outside deployments so that we don't block them. Note that while adding an index
    #   is a schema change, it's completely safe to run the operation after the code has deployed.
    # Once deployed, run these manually via: https://develop.sentry.dev/database-migrations/#migration-deployment

    is_post_deployment = False

    dependencies = [
        ("sentry", "0840_savedsearch_type_non_null"),
        ("uptime", "0029_uptime_subscription_index_domain_cols"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectuptimesubscription",
            name="uptime_status_update_date",
            field=models.DateTimeField(db_default=django.db.models.functions.datetime.Now()),
        ),
        migrations.AddIndex(
            model_name="projectuptimesubscription",
            index=models.Index(
                fields=["uptime_status", "uptime_status_update_date"],
                name="uptime_proj_uptime__d0dce1_idx",
            ),
        ),
    ]
