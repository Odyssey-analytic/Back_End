import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

averageTriesPerLevel_aggregate_table = """
CREATE MATERIALIZED VIEW averageTriesPerLevel
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id,
    progression01, 
    COUNT(*) FILTER (WHERE progressionStatus = 'Fail')::float /
    COUNT(DISTINCT client) AS avg_tries
    FROM gameevent ge
    JOIN ProgeressionEvent pe 
    ON ge_id = pe_game_event
    GROUP BY product_id, bucket, progression01;
"""
averageTriesPerLevel_refresh_policy = """
SELECT add_continuous_aggregate_policy('averageTriesPerLevel',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0009_LevelCompletionRate')]
    
    operations = [
        migrations.RunSQL(averageTriesPerLevel_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW averageTriesPerLevel;"),
        migrations.RunSQL(averageTriesPerLevel_refresh_policy)

    ]




