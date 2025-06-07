import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

levelCompletionRate_aggregate_table = """
CREATE MATERIALIZED VIEW levelCompletionRate
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    progression01, 
    COUNT(*) FILTER (WHERE progressionStatus = 'Complete')::float /
    COUNT(*) AS completion_rate
    FROM gameevent ge
    JOIN ProgeressionEvent pe 
    ON ge_id = pe_game_event
    GROUP BY product_id, bucket, progression01;
"""
levelCompletionRate_refresh_policy = """
SELECT add_continuous_aggregate_policy('levelCompletionRate',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0008_ARPPU')]
    
    operations = [
        migrations.RunSQL(levelCompletionRate_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW levelCompletionRate;"),
        migrations.RunSQL(levelCompletionRate_refresh_policy)

    ]





