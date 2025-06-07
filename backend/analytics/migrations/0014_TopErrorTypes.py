import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

topErrorTypes_aggregate_table = """
CREATE MATERIALIZED VIEW topErrorTypes
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    message,
    COUNT(*) AS occurrences
    FROM gameevent ge
    JOIN ErrorEvent ee 
    ON ge_id = ee_game_event
    GROUP BY product_id, bucket, message
    ORDER BY occurrences DESC
    LIMIT 10;
"""
topErrorTypes_refresh_policy = """
SELECT add_continuous_aggregate_policy('topErrorTypes,
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0013_CrashRate')]
    
    operations = [
        migrations.RunSQL(topErrorTypes_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW topErrorTypes;"),
        migrations.RunSQL(topErrorTypes_refresh_policy)

    ]


