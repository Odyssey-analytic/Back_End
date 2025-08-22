import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.fields
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

averageFPS_aggregate_table = """
CREATE MATERIALIZED VIEW averageFPS
WITH (timescaledb.continuous) AS 
SELECT
    time_bucket('1 hour', time) AS bucket,
    product_id, 
    AVG(FPS) AS average_FPS
    FROM gameevent ge
    JOIN qualityevent qe 
    ON ge_id = qe_game_event
    GROUP BY product_id, bucket;
"""
averageFPS_refresh_policy = """
SELECT add_continuous_aggregate_policy('averageFPS',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '15 minutes');
"""

averageFPS_conditions = """
ALTER MATERIALIZED VIEW averageFPS
SET (timescaledb.materialized_only = false);
"""


class Migration(migrations.Migration):
    initial = False
    atomic = False

    dependencies = [('analytics', '0003_DailyActiveUsers')]
    
    operations = [
        migrations.RunSQL(averageFPS_aggregate_table, reverse_sql="DROP MATERIALIZED VIEW averageFPS;"),
        migrations.RunSQL(averageFPS_refresh_policy),
        migrations.RunSQL(averageFPS_conditions)

    ]
