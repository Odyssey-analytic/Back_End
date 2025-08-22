import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

resourceSinkRatio_aggregate_table = """
CREATE MATERIALIZED VIEW resourceSinkRatio
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    re."itemType", 
    SUM(CASE WHEN re."flowType" = 'Sink' THEN amount ELSE 0 END)::float /
    SUM(amount) AS sink_ratio
    FROM gameevent ge
    JOIN analytics_resourceevent re 
    ON ge.id = re.game_event
    GROUP BY product_id, bucket, re."itemType";
"""
resourceSinkRatio_refresh_policy = """
SELECT add_continuous_aggregate_policy('resourceSinkRatio',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0011_NetResourceFlow')]
    
    operations = [
        migrations.RunSQL(resourceSinkRatio_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW resourceSinkRatio;"),
        migrations.RunSQL(resourceSinkRatio_refresh_policy)

    ]





