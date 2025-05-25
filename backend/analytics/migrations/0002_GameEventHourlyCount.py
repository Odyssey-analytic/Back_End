import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

gameeventCount_hourly_aggregate_table = """
CREATE MATERIALIZED VIEW gameeventCount_hourly
WITH (timescaledb.continuous) AS 
SELECT 
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    count(*) AS event_count
    FROM gameevent
    GROUP BY bucket, product_id;
"""
gameeventCount_hourly_refresh_policy = """
SELECT add_continuous_aggregate_policy('gameeventCount_hourly',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""

gameeventCount_hourly_conditions = """
ALTER MATERIALIZED VIEW gameeventCount_hourly
SET (timescaledb.materialized_only = false);
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0001_initial')]
    
    operations = [
        migrations.RunSQL(gameeventCount_hourly_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW gameeventCount_hourly;"),
        migrations.RunSQL(gameeventCount_hourly_refresh_policy),
        migrations.RunSQL(gameeventCount_hourly_conditions)

    ]