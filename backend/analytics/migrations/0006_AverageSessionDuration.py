import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

averageSessionDuration_aggregate_table = """
CREATE MATERIALIZED VIEW averageSessionDuration
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    AVG(s."duration") AS average_session_duration
    FROM gameevent ge
    JOIN analytics_session s 
    ON ge.session_id = s.id
    WHERE s."duration" IS NOT NULL
    GROUP BY product_id, bucket;
"""
averageSessionDuration_refresh_policy = """
SELECT add_continuous_aggregate_policy('averageSessionDuration',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0005_AverageMemoryUsage')]
    
    operations = [
        migrations.RunSQL(averageSessionDuration_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW averageSessionDuration;"),
        migrations.RunSQL(averageSessionDuration_refresh_policy)

    ]


