import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

crashRate_aggregate_table = """
CREATE MATERIALIZED VIEW crashRate
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    COUNT(*) FILTER (WHERE severity = 'Critical')::float /
    COUNT(DISTINCT session_id) AS crash_rate
    FROM gameevent ge
    LEFT JOIN analytics_errorevent ee 
    ON ge.id = ee.game_event
    GROUP BY product_id, bucket;
"""
crashRate_refresh_policy = """
SELECT add_continuous_aggregate_policy('crashRate',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0012_ResourceSinkRatio')]
    
    operations = [
        migrations.RunSQL(crashRate_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW crashRate;"),
        migrations.RunSQL(crashRate_refresh_policy)

    ]

